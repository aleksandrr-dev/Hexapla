// Credits a licence REQUIRES at the head of a translation's column - not the
// courtesy credits, which live in the About text. Android shows the same line
// from BibleRepo.columnCredit; keep the two in step.
//
// kie: OsmKelam's permission (2026-09-25) is conditional on their link heading
// the column of Ottoman texts, «with explanation that the originals may be
// compared here». A © heads the column on every chapter; the link and the
// explanation are one tap
// away (owner: OsmKelam OK for web and app; «the symbol per chapter», 2026-09-25).

export interface ColumnCredit {
  /** Always visible at the head of the column. */
  short: string;
  /** The explanation, shown in a sheet from the short line. */
  text: string;
  url: string;
  lang: string;
}

const OSMKELAM: ColumnCredit = {
  short: "©",
  // The last two sentences point readers at OsmKelam's own word notes: their
  // e-mail of 2026-11-20 asked that readers be sent to them (owner: «Yes»).
  text:
    "Osmanlıca metinlerin Latin harfli transkripsiyonu: © Osmanlıca Kelâm. " +
    "Orijinal metinler aşağıdaki bağlantıda karşılaştırılabilir. " +
    "Günümüz Türkçesinde anlamı değişmiş sözcüklerin açıklama notları da oradadır: " +
    "örneğin Osmanlıcada «heykel» yontu değil, mabet demektir.",
  url: "https://osmanlicakelam.net/osm/metinler",
  lang: "tr",
};

const CREDITS: Record<string, ColumnCredit> = { kie: OSMKELAM };

// kie's apocrypha (book >= 66) are Ali Bey 1665 in Kadir Akın's transliteration,
// not OsmKelam's: their © heads the canon only (owner, 2026-09-29).
export function columnCredit(id: string, book: number): ColumnCredit | undefined {
  if (id === "kie" && book >= 66) return undefined;
  return CREDITS[id];
}
