# Renders text runs to tight transparent PNGs via WPF/DirectWrite, which
# shapes complex scripts (Tamil, Devanagari...) correctly — PIL's basic
# FreeType path cannot (no Raqm in the Windows wheels), so the store-asset
# generators (make_reader_shot.py, make_feature_graphic.py) shell out to
# this for such languages and paste the resulting PNGs.
#
# Usage: powershell -File render_text.ps1 -Manifest items.json
# Manifest: JSON array of {text, font, size, color, wrap, maxwidth, out,
#   culture, rtl}.
#   wrap=true  -> word-wrap at maxwidth (block of lines, natural leading)
#   wrap=false -> single line; if maxwidth given, shrink size to fit
#   culture    -> BCP-47 tag for shaping/typography (default: script-neutral
#                 "en-US" — do NOT default to a specific language's culture,
#                 it previously hardcoded ta-IN for every script, which risks
#                 wrong digit-substitution/OpenType feature selection for
#                 unrelated languages like Arabic or Hebrew)
#   rtl        -> true for right-to-left scripts (Arabic, Hebrew); controls
#                 FlowDirection so paragraph anchoring and embedded
#                 LTR runs (e.g. a Latin verse number) resolve correctly
param([Parameter(Mandatory = $true)][string]$Manifest)

Add-Type -AssemblyName PresentationCore, WindowsBase

$items = Get-Content -Raw -Encoding UTF8 $Manifest | ConvertFrom-Json

foreach ($it in $items) {
    $c = [Windows.Media.Color]::FromRgb(
        [Convert]::ToByte($it.color.Substring(1, 2), 16),
        [Convert]::ToByte($it.color.Substring(3, 2), 16),
        [Convert]::ToByte($it.color.Substring(5, 2), 16))
    $brush = New-Object Windows.Media.SolidColorBrush $c
    $tf = New-Object Windows.Media.Typeface $it.font
    $size = [double]$it.size
    $cultureTag = if ($it.culture) { $it.culture } else { "en-US" }
    $culture = [Globalization.CultureInfo]::GetCultureInfo($cultureTag)
    $flow = if ($it.rtl) { [Windows.FlowDirection]::RightToLeft } else { [Windows.FlowDirection]::LeftToRight }

    while ($true) {
        $fmt = New-Object Windows.Media.FormattedText(
            [string]$it.text, $culture,
            $flow, $tf, $size, $brush, 1.0)
        if ($it.wrap) {
            $fmt.MaxTextWidth = [double]$it.maxwidth
            break
        }
        if (-not $it.maxwidth -or
            $fmt.WidthIncludingTrailingWhitespace -le [double]$it.maxwidth -or
            $size -le 20) { break }
        $size -= 2
    }

    if ($it.wrap) { $w = [int][Math]::Ceiling([double]$it.maxwidth) }
    else { $w = [int][Math]::Ceiling($fmt.WidthIncludingTrailingWhitespace) }
    $h = [int][Math]::Ceiling($fmt.Height)

    # RTL + no MaxTextWidth (single-line, unwrapped) is a WPF quirk: text
    # extends leftward from the origin into negative-x space and gets
    # clipped by the bitmap bounds. Shifting the origin to the right edge
    # keeps the glyphs inside [0, w).
    $originX = if ($it.rtl -and -not $it.wrap) { $w } else { 0 }
    $dv = New-Object Windows.Media.DrawingVisual
    $dc = $dv.RenderOpen()
    $dc.DrawText($fmt, (New-Object Windows.Point $originX, 0))
    $dc.Close()
    $rtb = New-Object Windows.Media.Imaging.RenderTargetBitmap(
        $w, $h, 96, 96, [Windows.Media.PixelFormats]::Pbgra32)
    $rtb.Render($dv)
    $enc = New-Object Windows.Media.Imaging.PngBitmapEncoder
    $enc.Frames.Add([Windows.Media.Imaging.BitmapFrame]::Create($rtb))
    $fs = [IO.File]::Create($it.out)
    $enc.Save($fs)
    $fs.Close()
    Write-Output ("rendered {0} ({1}x{2}, size {3})" -f $it.out, $w, $h, $size)
}
