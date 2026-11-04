import { fatigueColor, muscleLabel } from '../../lib/muscles'

type Shape = { muscle: string; d: string }

/** Mirror a path drawn on the left half (x < 60) to the right half of a 120-wide figure. */
function mirror(d: string): string {
  return d.replace(/(-?\d+(?:\.\d+)?),(-?\d+(?:\.\d+)?)/g, (_, x, y) => `${120 - Number(x)},${y}`)
}

/** Shapes drawn once for the left side and mirrored. */
function both(muscle: string, d: string): Shape[] {
  return [
    { muscle, d },
    { muscle, d: mirror(d) },
  ]
}

const OUTLINE =
  'M60,6 C68,6 72,12 72,20 C72,27 68,32 64,34 L64,38 C74,40 84,42 88,48 C93,56 94,68 95,80 L98,104 C99,112 97,116 94,116 ' +
  'L90,104 C88,96 86,86 84,78 L82,96 C82,108 84,118 84,128 L82,170 C81,184 80,200 78,214 L76,232 C75,238 70,238 69,232 ' +
  'L66,180 C65,166 62,150 60,140 C58,150 55,166 54,180 L51,232 C50,238 45,238 44,232 L42,214 C40,200 39,184 38,170 ' +
  'L36,128 C36,118 38,108 38,96 L36,78 C34,86 32,96 30,104 L26,116 C23,116 21,112 22,104 L25,80 C26,68 27,56 32,48 ' +
  'C36,42 46,40 56,38 L56,34 C52,32 48,27 48,20 C48,12 52,6 60,6 Z'

const FRONT: Shape[] = [
  ...both('front_delts', 'M36,44 C41,41 47,41 50,44 L48,54 C43,55 38,54 34,52 Z'),
  ...both('side_delts', 'M30,50 C31,46 33,44 36,44 L34,52 L31,58 Z'),
  ...both('chest', 'M50,46 L59,46 L59,64 C54,66 47,65 43,60 L48,54 Z'),
  ...both('biceps', 'M30,60 C33,58 36,58 37,62 L35,78 C33,80 30,80 29,77 Z'),
  ...both('forearms', 'M28,82 C31,80 34,80 35,83 L31,104 C29,106 26,105 25,102 Z'),
  ...both('obliques', 'M44,66 L50,68 L50,92 L42,94 C41,86 41,76 44,66 Z'),
  { muscle: 'abs', d: 'M51,66 L69,66 L69,96 C64,100 56,100 51,96 Z' },
  ...both('quads', 'M41,104 C45,100 52,102 55,108 L55,150 C52,160 47,162 44,156 C40,140 39,122 41,104 Z'),
  ...both('adductors', 'M55,110 L59,112 L58,140 L55,146 Z'),
  ...both('tibialis', 'M44,180 C46,176 49,176 50,180 L48,214 C47,216 45,216 45,214 Z'),
]

const BACK: Shape[] = [
  ...both('rear_delts', 'M34,46 C38,42 45,42 48,45 L46,54 C41,55 37,54 33,52 Z'),
  ...both('side_delts', 'M30,50 C31,46 33,44 34,46 L33,52 L31,58 Z'),
  { muscle: 'upper_back', d: 'M50,40 L70,40 L74,46 L68,62 L60,66 L52,62 L46,46 Z' },
  ...both('lats', 'M46,56 L52,64 L56,86 L46,90 C42,80 42,66 46,56 Z'),
  ...both('triceps', 'M30,58 C33,56 36,56 37,60 L35,78 C33,80 30,80 29,77 Z'),
  ...both('forearms', 'M28,82 C31,80 34,80 35,83 L31,104 C29,106 26,105 25,102 Z'),
  { muscle: 'lower_back', d: 'M54,70 L66,70 L68,96 L60,100 L52,96 Z' },
  ...both('abductors', 'M38,100 L44,98 L46,112 L38,116 Z'),
  ...both('glutes', 'M45,100 C50,98 57,99 59,104 L59,124 C54,128 47,127 43,122 Z'),
  ...both('hamstrings', 'M42,128 C46,126 53,127 56,130 L54,160 C51,166 46,166 44,160 Z'),
  ...both('calves', 'M43,176 C46,172 51,172 53,178 L51,202 C49,206 45,206 44,202 Z'),
]

/** One view of the figure with muscles coloured by fatigue. */
function Figure(props: { shapes: Shape[]; levels: Record<string, number>; label: string; size: number }) {
  return (
    <figure className="body-figure">
      <svg viewBox="0 0 120 240" width={props.size * 0.5} height={props.size} role="img" aria-label={`${props.label} muscles`}>
        <path d={OUTLINE} fill="#20242d" stroke="#3a404d" strokeWidth="1" />
        {props.shapes.map((s, i) => (
          <path key={i} d={s.d} fill={fatigueColor(props.levels[s.muscle] ?? 0)} stroke="#0f1115" strokeWidth="0.8">
            <title>
              {muscleLabel(s.muscle)}: {Math.round((props.levels[s.muscle] ?? 0) * 100)}%
            </title>
          </path>
        ))}
      </svg>
      <figcaption className="muted">{props.label}</figcaption>
    </figure>
  )
}

/** Front and back views side by side. */
export default function BodyMap(props: { levels: Record<string, number>; size?: number }) {
  const size = props.size ?? 260
  return (
    <div className="body-map">
      <Figure shapes={FRONT} levels={props.levels} label="Front" size={size} />
      <Figure shapes={BACK} levels={props.levels} label="Back" size={size} />
    </div>
  )
}
