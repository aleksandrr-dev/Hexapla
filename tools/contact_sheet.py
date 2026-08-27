#!/usr/bin/env python
"""
contact_sheet.py - tile many small zoom crops into ONE labelled image.

WHY THIS EXISTS
---------------
In vision transcription the token cost is dominated by IMAGE INPUT, and image
input scales with pixel area. Running more agents in parallel does not reduce
that cost at all - it spends the same tokens faster and burns the rolling usage
limit sooner. The only real lever is sending fewer, smaller images.

The primary read (a full page strip, ~4,000 tokens) is NOT where to economise:
that is the actual transcription and its resolution is the accuracy. The waste
is in the SECONDARY reads - the dozen-plus individual zoom crops taken to
adjudicate diacritics and uncertain letters, one Read per mark. A single
session spent ~22 separate reads on those.

This tiles them into one sheet. Twenty marks at 12x on one image costs roughly
what two or three separate crops did, and it is also a BETTER read: the marks
sit side by side at identical scale, which is exactly the in-line-control
comparison the method wants.

USAGE
-----
    python tools/contact_sheet.py <image> <out.png> [--scale N] [--cols N] \\
        --box x0,y0,x1,y1,LABEL  [--box ... ]

    # or pass a JSON file of boxes: [[x0,y0,x1,y1,"label"], ...]
    python tools/contact_sheet.py <image> <out.png> --boxes sites.json

    # boxes may instead be [{"image":..., "box":[x0,y0,x1,y1], "label":...}],
    # which lets ONE sheet mix crops from several strips (pass '-' as <image>).
    # kxii_marks.py emits exactly that form.
    python tools/contact_sheet.py - <out.png> --boxes boxes.json

Then Read <out.png> ONCE and adjudicate every site from it. Only go back for a
single crop if a site is still genuinely undecidable on the sheet.

⚠ A site that is illegible on the sheet is still flagged, never guessed. The
sheet reduces cost, it does not lower the evidence bar.
"""
import argparse
import io
import json
import os
import sys

from PIL import Image, ImageDraw


def build(image_path, boxes, tile_h, max_width, pad, label_h):
    """Row-pack tiles normalised to a common HEIGHT.

    Uniform max-size cells are a trap: one wide crop inflates every cell and
    the sheet ends up costing more than the separate reads it replaced (a
    first version of this tool measured 12,800 tokens for three sites).
    Normalising to a common height keeps marks comparable at a glance - which
    is the whole point of a sheet - while row-packing charges only for the
    pixels each crop actually needs.
    """
    cache = {}

    def _src(path):
        if path not in cache:
            cache[path] = Image.open(path).convert("RGB")
        return cache[path]

    tiles = []
    for box in boxes:
        # A box is either [x0,y0,x1,y1,label] against `image_path`, or a dict
        # {"image":..., "box":[...], "label":...} so ONE sheet can mix crops
        # from several strips. Before that, a chapter whose sites sat on four
        # strips cost four sheets - four image reads to adjudicate one pass.
        if isinstance(box, dict):
            path = box.get("image") or image_path
            x0, y0, x1, y1 = (int(v) for v in box["box"][:4])
            label = str(box.get("label", ""))
        else:
            path = image_path
            x0, y0, x1, y1 = (int(v) for v in box[:4])
            label = str(box[4]) if len(box) > 4 else ""
        crop = _src(path).crop((x0, y0, x1, y1))
        if crop.height < 1 or crop.width < 1:
            continue
        w = max(1, int(round(crop.width * tile_h / float(crop.height))))
        tiles.append((crop.resize((w, tile_h), Image.LANCZOS), label))

    if not tiles:
        raise SystemExit("no boxes given")

    # row-pack
    rows, cur, cur_w = [], [], 0
    for tile, label in tiles:
        need = tile.width + pad
        if cur and cur_w + need > max_width:
            rows.append(cur)
            cur, cur_w = [], 0
        cur.append((tile, label))
        cur_w += need
    if cur:
        rows.append(cur)

    row_h = tile_h + label_h + pad
    sheet_w = min(
        max_width,
        max(sum(t.width + pad for t, _ in r) for r in rows) + pad,
    )
    sheet = Image.new("RGB", (sheet_w, len(rows) * row_h + pad), (255, 255, 255))
    draw = ImageDraw.Draw(sheet)

    y = pad
    for row in rows:
        x = pad
        for tile, label in row:
            sheet.paste(tile, (x, y + label_h))
            draw.text((x + 2, y + 1), label, fill=(0, 0, 0))
            draw.rectangle(
                [x - 1, y + label_h - 1, x + tile.width, y + label_h + tile.height],
                outline=(160, 160, 160),
            )
            x += tile.width + pad
        y += row_h
    return sheet


def parse_box(text):
    parts = text.split(",")
    if len(parts) < 4:
        raise argparse.ArgumentTypeError(
            "box must be x0,y0,x1,y1[,label] - got %r" % text
        )
    return parts[:4] + ([",".join(parts[4:])] if len(parts) > 4 else [])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("image", help="strip png; pass '-' when every box in "
                                  "--boxes carries its own \"image\"")
    ap.add_argument("out")
    ap.add_argument("--box", action="append", type=parse_box, default=[])
    ap.add_argument("--boxes", help="JSON file: [[x0,y0,x1,y1,label], ...]")
    ap.add_argument(
        "--tile-h",
        type=int,
        default=200,
        help="every crop is scaled to this height (default 200). A ~30px "
        "diacritic mark at 200px is roughly 7x; use 300 for a hard call.",
    )
    ap.add_argument("--max-width", type=int, default=1400)
    ap.add_argument("--pad", type=int, default=10)
    ap.add_argument("--label-h", type=int, default=14)
    args = ap.parse_args(argv)

    boxes = list(args.box)
    if args.boxes:
        boxes.extend(json.load(io.open(args.boxes, encoding="utf-8")))
    if args.image != "-" and not os.path.isfile(args.image):
        raise SystemExit("no such image: %s" % args.image)
    if args.image == "-" and not all(isinstance(b, dict) and b.get("image")
                                     for b in boxes):
        raise SystemExit("image '-' requires every box to carry its own \"image\"")

    sheet = build(
        args.image, boxes, args.tile_h, args.max_width, args.pad, args.label_h
    )
    sheet.save(args.out)
    approx = int(sheet.width * sheet.height / 750)
    print(
        "%s  %dx%d  %d sites at tile-h=%d  (~%d image tokens for the whole sheet)"
        % (args.out, sheet.width, sheet.height, len(boxes), args.tile_h, approx)
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
