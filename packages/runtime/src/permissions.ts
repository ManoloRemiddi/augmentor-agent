// Copyright © 2026 Manolo Remiddi · SPDX-License-Identifier: LicenseRef-Augmentor-MIT-Resale-1.0

// Recognise only literal, single-command queries. Anything outside this small
// grammar retains the normal approval policy; this is not a shell sandbox.
function literalWords(command: string): string[] | undefined {
  if (!command.trim() || /[\x00-\x1f\x7f$`\\;|&<>(){}*?\[\]~!#]/.test(command)) return;
  const words: string[] = [];
  let word = '', quote = '', started = false;
  for (const char of command) {
    if (quote) {
      if (char === quote) quote = '';
      else word += char;
    } else if (char === "'" || char === '"') {
      quote = char;
      started = true;
    } else if (char === ' ') {
      if (started) words.push(word);
      word = '';
      started = false;
    } else {
      word += char;
      started = true;
    }
  }
  if (quote) return;
  if (started) words.push(word);
  return words;
}

const queryFlags: Record<string, ReadonlySet<string>> = {
  pwd: new Set(['-L', '-P']),
  whoami: new Set(),
  id: new Set(['-u', '-g', '-G', '-n', '-r', '-un', '-gn', '-Gn']),
  uname: new Set(['-a', '-s', '-n', '-r', '-v', '-m', '-p', '-i', '-o', '--all']),
  uptime: new Set(['-p', '-s', '--pretty', '--since']),
  free: new Set(['-b', '-k', '-m', '-g', '-h', '--human', '--si', '-w', '--wide']),
  df: new Set(['-h', '-H', '-k', '-T', '-i', '-P', '-a', '-l', '--human-readable']),
};

export function isRoutineQuery(command: unknown): boolean {
  if (typeof command !== 'string') return false;
  const words = literalWords(command);
  if (!words?.length) return false;
  const [executable, ...args] = words;
  const name = executable.replace(/^\/(?:usr\/)?bin\//, '');
  if (name === 'date') {
    let format = false;
    return args.every(arg => {
      if (arg.startsWith('+')) {
        if (format) return false;
        format = true;
        return true;
      }
      // In particular, never accept -s/--set or positional clock-setting dates.
      return /^(?:-u|--utc|--universal|-R|--rfc-email|-I|--iso-8601(?:=(?:date|hours|minutes|seconds|ns))?|-I(?:date|hours|minutes|seconds|ns)|--rfc-3339=(?:date|seconds|ns))$/.test(arg);
    });
  }
  const flags = Object.hasOwn(queryFlags, name) ? queryFlags[name] : undefined;
  return !!flags && args.every(arg => flags.has(arg));
}
