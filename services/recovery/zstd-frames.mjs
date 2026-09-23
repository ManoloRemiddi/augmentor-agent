// SPDX-License-Identifier: MIT
// Frame scanner from @deepseek-ai/dsh-session-persistence-jsonl 0.1.5-rc.1.
// https://github.com/deepseek-ai/deepseek-harness/tree/main/packages/session/session-persistence-jsonl
/*
MIT License

Copyright (c) 2026 DeepSeek

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
*/
const ZSTD_MAGIC = 4247762216;
export function scanZstdFrames(buffer, maxFrames = Number.POSITIVE_INFINITY) {
	const frames = [];
	let offset = 0;
	while (offset < buffer.length) {
		const start = offset;
		if (buffer.length - offset < 4) return {
			frames,
			tornStart: start
		};
		if (buffer.readUInt32LE(offset) !== ZSTD_MAGIC) throw new Error(`corrupt Zstandard session log: invalid frame magic at byte ${offset}`);
		offset += 4;
		if (offset === buffer.length) return {
			frames,
			tornStart: start
		};
		const descriptor = buffer.readUInt8(offset);
		offset += 1;
		if ((descriptor & 24) !== 0) throw new Error(`corrupt Zstandard session log: reserved frame-header bit at byte ${offset - 1}`);
		const contentSizeFlag = descriptor >>> 6;
		const singleSegment = (descriptor & 32) !== 0;
		const checksum = (descriptor & 4) !== 0;
		const dictionaryFlag = descriptor & 3;
		const dictionaryBytes = dictionaryFlag === 3 ? 4 : dictionaryFlag;
		const contentSizeBytes = contentSizeFlag === 0 ? singleSegment ? 1 : 0 : 1 << contentSizeFlag;
		const remainingHeaderBytes = (singleSegment ? 0 : 1) + dictionaryBytes + contentSizeBytes;
		if (buffer.length - offset < remainingHeaderBytes) return {
			frames,
			tornStart: start
		};
		offset += remainingHeaderBytes;
		for (;;) {
			if (buffer.length - offset < 3) return {
				frames,
				tornStart: start
			};
			const blockHeader = buffer.readUIntLE(offset, 3);
			offset += 3;
			const lastBlock = (blockHeader & 1) !== 0;
			const blockType = blockHeader >>> 1 & 3;
			const blockSize = blockHeader >>> 3;
			if (blockType === 3) throw new Error(`corrupt Zstandard session log: reserved block type at byte ${offset - 3}`);
			const payloadBytes = blockType === 1 ? 1 : blockSize;
			if (buffer.length - offset < payloadBytes) return {
				frames,
				tornStart: start
			};
			offset += payloadBytes;
			if (lastBlock) break;
		}
		if (checksum) {
			if (buffer.length - offset < 4) return {
				frames,
				tornStart: start
			};
			offset += 4;
		}
		frames.push({
			start,
			end: offset
		});
		if (frames.length === maxFrames) return { frames };
	}
	return { frames };
}
