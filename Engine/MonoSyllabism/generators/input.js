import { collector } from '../utilities/stream.js';
import mapperNormalize from '../map/loader.js';
import { InputFile } from '../../Bridge/path.js';
/**
 * Generator: raw file → complete WASM mapperNormalize (masked ASCII internal).
 * Yields mapped blocks ready for the segmentor.
 * NOT file writing — belongs to object (memory/mapping).
 */
export async function* readAndPrepare(inputFile = InputFile()) {
  for await (const block of collector(inputFile)) {
    // The raw normalize stage alone does not mask Latin/digit blocks; the
    // segmentor must receive the complete encoder, not unprotected English.
    yield mapperNormalize(block);
  }
}