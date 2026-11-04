/** Parse a user-typed number, accepting a comma decimal separator (iOS PL keyboard). */
export function parseDecimal(input: string): number | null {
  const normalized = input.trim().replace(',', '.')
  if (!/^\d+(\.\d+)?$|^\.\d+$/.test(normalized)) return null
  return Number(normalized)
}
