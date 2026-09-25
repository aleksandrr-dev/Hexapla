// Credits a licence REQUIRES at the head of a translation's column - not the
// courtesy credits, which live in the About text. Android shows the same line
// from BibleRepo.columnCredit; keep the two in step.
//
// kie: OsmKelam's permission (2026-09-25) is conditional on their link heading
// the column of Ottoman texts, «with explanation that the originals may be
// compared here». The link itself is always visible; the explanation is one tap
// away (owner reported their OK for web and app, 2026-09-25).

export interface ColumnCredit {
  /** Always visible at the head of the column. */
  short: string;
  /** The explanation, shown in a sheet from the short line. */
  text: string;
  url: string;
  lang: string;
}

const OSMKELAM: ColumnCredit = {
  short: "© osmanlicakelam.net/osm/metinler",
  text: "Osmanlıca metinlerin Latin harfli transkripsiyonu: © Osmanlıca Kelâm. Orijinal metinler aşağıdaki bağlantıda karşılaştırılabilir.",
  url: "https://osmanlicakelam.net/osm/metinler",
  lang: "tr",
};

const CREDITS: Record<string, ColumnCredit> = { kie: OSMKELAM };

export function columnCredit(id: string): ColumnCredit | undefined {
  return CREDITS[id];
}
