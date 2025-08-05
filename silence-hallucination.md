Here’s what I found about faster‑whisper (or Whisper-based) hallucinations when you transcribe very short or silent recordings:

---

## 1. ✅ What happens: hallucinations on silence or ultra‑short audio

* Faster‑Whisper (and Whisper models generally) often **generates plausible phrases** from completely silent or ultra-short audio—e.g. "okay all right", "thank you for watching"—even when no one speaks. This is a known behavior and quite common. ([GitHub][1])
* A major study showed that **around 40%** of non‑speech inputs (silence/noise) caused hallucinations. For 1‑second silent clips, about **52%** produced hallucinated text. ([arXiv][2])

---

## 2. ⚙️ Why it happens

* Whisper treats transcription like an LLM: even silent input it "expects" speech, and so **hallucinates based on learned patterns** from training data—often common phrases in video transcripts like “thank you for listening”. ([Reddit][3])
* The model tends to **rely on its internal language model**, especially for very short chunks, sometimes looping repeated text across segments. ([Reddit][3])

---

## 3. 🛠 Solutions & mitigations

### A. Pre‑processing with Voice Activity Detection (VAD)

* Detect and remove silent or non‑speech audio using tools like **SileroVAD** or WebRTC VAD before sending input to Whisper. This greatly reduces hallucinations. ([arXiv][2])

### B. Model inference parameter tuning

* Setting **beam\_size = 1** minimizes hallucination rate compared to higher beam sizes. And enabling a **silence threshold** (e.g. minimum non-speech duration to skip) can further help. ([arXiv][2])
* In particular, a silence threshold of \~10–20 s reduced hallucination detection to \~15–16%. ([arXiv][2])

### C. Post‑processing filters (Bag of Hallucinations + deooping)

* Build a “bag” of frequent hallucinatory phrases (like “thank you for watching”) and filter them out. Combined with removing repeated segments ("looping"), this can significantly reduce hallucinations. ([arXiv][2])

### D. Model fine‑tuning: Calm‑Whisper

* A new research variant, called **Calm‑Whisper** (fine‑tuned on non‑speech), suppresses hallucinations by over 80% while minimally affecting real speech transcription. ([arXiv][4])

---

## 4. ✅ Recommendations for your scenario

You’re triggering hallucinations because your recordings are extremely short (<<1 s) and often silent. Here’s a practical plan:

1. **Add VAD in your pipeline**: discard or skip chunks shorter than, say, 0.5 s with no detected speech.
2. Use **beam\_size = 1** and configure a silence‑skip threshold if supported by faster-whisper.
3. Optionally, maintain a **filter list of known hallucinated phrases**, and post‑process transcripts to remove them.
4. If you need industrial-grade reliability, consider trying **Calm‑Whisper** or fine‑tuning same.

---

### Summary Table

| Symptom                       | Cause                              | Recommended Fix                             |
| ----------------------------- | ---------------------------------- | ------------------------------------------- |
| Hallucination on silence      | Model expects text anyway          | Use VAD to skip silent input                |
| Repeating phrases / "looping" | Chunk context issues / beam search | Set `beam_size=1`, disable context chaining |
| Frequent false phrases        | Learned from training corpus       | Filter via post‑processing (BoH)            |
| Overall hallucination conc.   | Model architecture and training    | Try Calm‑Whisper or select fine-tuning      |

---

## ✅ Final Thoughts

* This is a **well‑documented issue** with Whisper and faster‑whisper—especially on very short or silent inputs. Hallucination rates of **\~50%** for 1-second silence are typical. ([arXiv][2], [YouTube][5], [GitHub][6])
* Confidence: \~ 95% that your symptoms match the known phenomenon.
* Low complexity fixes (VAD + beam\_size=1 + filtering) usually solve most cases.
* If you’d like help wiring any step into your Python code, feel free to ask!

Uncertainty Map: I’m least confident about whether your version of faster‑whisper supports the exact same silence‑threshold flags. Checking documentation or your version release notes could be helpful.

[1]: https://github.com/guillaumekln/faster-whisper/issues/183?utm_source=chatgpt.com "Low performance on silent audios · Issue #183"
[2]: https://arxiv.org/html/2501.11378v1?utm_source=chatgpt.com "Investigation of Whisper ASR Hallucinations ..."
[3]: https://www.reddit.com/r/OpenAI/comments/1c3b7e8/openais_whisper_filled_in_silent_part_at_the/?utm_source=chatgpt.com "OpenAI's Whisper filled in silent part at the beginning of ..."
[4]: https://arxiv.org/abs/2505.12969?utm_source=chatgpt.com "Calm-Whisper: Reduce Whisper Hallucination On Non-Speech By Calming Crazy Heads Down"
[5]: https://www.youtube.com/shorts/-8pujgUgiD4?utm_source=chatgpt.com "OpenAI Whisper's crazy hallucinations during long stretches of ..."
[6]: https://github.com/openai/whisper/discussions/679?utm_source=chatgpt.com "A possible solution to Whisper hallucination #679"
