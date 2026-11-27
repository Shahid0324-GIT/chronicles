import type { ThemeMotif } from "@/features/narrative/contracts";

const spark = (x: number, y: number, r: number) =>
  `M${x} ${y - r}L${x + r / 3} ${y - r / 3}L${x + r} ${y}L${x + r / 3} ${y + r / 3}L${x} ${y + r}L${x - r / 3} ${y + r / 3}L${x - r} ${y}L${x - r / 3} ${y - r / 3}Z`;

/** Abstract artwork in the story's colours, until real images exist. */
export default function Motif({ kind }: { kind: ThemeMotif }) {
  return (
    <svg
      className={`story-motif ${kind}`}
      viewBox="0 0 400 400"
      aria-hidden="true"
    >
      <circle className="halo" cx="200" cy="200" r="160" />
      <circle className="disc" cx="200" cy="200" r="122" />
      {kind === "stars" && (
        <>
          <path
            className="warm"
            d="M236 128a86 86 0 1 0 34 128a70 70 0 1 1-34-128z"
          />
          <path className="cool" d={spark(104, 120, 30)} />
          <path className="light" d={spark(312, 292, 20)} />
          <path className="cool" d={spark(318, 96, 10)} />
        </>
      )}
      {kind === "branches" && (
        <>
          <path
            className="stroke"
            d="M200 372V210M200 270l-70-80M200 240l78-80M130 190l-34-72M130 190l38-82M278 160l-30-76M278 160l52-48"
          />
          <circle className="warm" cx="96" cy="110" r="17" />
          <circle className="cool" cx="168" cy="98" r="13" />
          <circle className="warm" cx="248" cy="76" r="19" />
          <circle className="cool" cx="336" cy="106" r="12" />
        </>
      )}
      {kind === "waves" && (
        <>
          <circle className="warm" cx="262" cy="138" r="38" />
          <path
            className="stroke cool-line"
            d="M62 214q35-34 70 0t70 0 70 0 66 0"
          />
          <path className="stroke" d="M78 258q31-30 62 0t62 0 62 0 56 0" />
          <path
            className="stroke cool-line"
            d="M110 300q23-24 46 0t46 0 46 0 40 0"
          />
        </>
      )}
      {kind === "peaks" && (
        <>
          <circle className="warm" cx="270" cy="128" r="34" />
          <path className="cool" d="M78 292L168 150l90 142z" />
          <path className="light" d="M168 150l26 42-26-10-24 12z" />
          <path className="warm soft" d="M180 292l74-104 72 104z" />
        </>
      )}
      {kind === "embers" && (
        <>
          <path
            className="warm"
            d="M204 84c14 62 76 78 76 150a80 80 0 0 1-160 0c0-34 18-50 34-66 2 24 12 34 24 38-12-46 2-86 26-122z"
          />
          <path
            className="light soft"
            d="M204 214c8 28 34 36 34 66a36 36 0 0 1-72 0c0-30 28-34 38-66z"
          />
          <circle className="cool" cx="114" cy="122" r="7" />
          <circle className="warm" cx="294" cy="108" r="9" />
          <circle className="cool" cx="308" cy="178" r="5" />
        </>
      )}
      {kind === "rings" && (
        <>
          <circle className="stroke" cx="200" cy="200" r="88" />
          <circle className="stroke cool-line" cx="200" cy="200" r="54" />
          <circle className="warm" cx="200" cy="200" r="22" />
          <circle className="cool" cx="262" cy="138" r="13" />
          <circle className="light" cx="126" cy="248" r="8" />
        </>
      )}
    </svg>
  );
}
