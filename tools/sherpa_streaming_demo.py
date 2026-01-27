import os
import sys
import time
import numpy as np

SHERPA_SAMPLE_RATE = 16000
CHUNK_DURATION_MS = 100
CHUNK_SIZE = int(SHERPA_SAMPLE_RATE * CHUNK_DURATION_MS / 1000)

MODELS = {
    "standard": {
        "repo": "models--csukuangfj--sherpa-onnx-streaming-zipformer-en-20M-2023-02-17",
        "encoder": "encoder-epoch-99-avg-1.int8.onnx",
        "decoder": "decoder-epoch-99-avg-1.int8.onnx",
        "joiner": "joiner-epoch-99-avg-1.int8.onnx",
        "tokens": "tokens.txt",
    },
    "ort": {
        "repo": "models--bookbot--sherpa-onnx-ort-streaming-zipformer-en-2023-06-26",
        "encoder": "encoder-epoch-99-avg-1.int8.ort",
        "decoder": "decoder-epoch-99-avg-1.ort",
        "joiner": "joiner-epoch-99-avg-1.int8.ort",
        "tokens": "tokens.txt",
    },
}


def get_hf_cache_path():
    userprofile = os.environ.get('USERPROFILE')
    if not userprofile:
        userprofile = os.path.expanduser('~')
    return os.path.join(userprofile, '.cache', 'huggingface', 'hub')


def get_model_path(model_type="standard"):
    model_info = MODELS.get(model_type)
    if not model_info:
        print(f"Unknown model type: {model_type}")
        return None

    cache_base = get_hf_cache_path()
    model_dir = os.path.join(cache_base, model_info["repo"])

    if not os.path.exists(model_dir):
        print(f"Model directory not found: {model_dir}")
        return None

    snapshots_dir = os.path.join(model_dir, 'snapshots')
    if not os.path.exists(snapshots_dir):
        print(f"Snapshots directory not found: {snapshots_dir}")
        return None

    snapshots = os.listdir(snapshots_dir)
    if not snapshots:
        print("No snapshots found")
        return None

    return os.path.join(snapshots_dir, snapshots[0]), model_info


def create_recognizer(model_path, model_info):
    import sherpa_onnx

    encoder = os.path.join(model_path, model_info["encoder"])
    decoder = os.path.join(model_path, model_info["decoder"])
    joiner = os.path.join(model_path, model_info["joiner"])
    tokens = os.path.join(model_path, model_info["tokens"])

    for name, f in [("encoder", encoder), ("decoder", decoder), ("joiner", joiner), ("tokens", tokens)]:
        if not os.path.exists(f):
            print(f"Missing {name}: {f}")
            return None

    recognizer = sherpa_onnx.OnlineRecognizer.from_transducer(
        encoder=encoder,
        decoder=decoder,
        joiner=joiner,
        tokens=tokens,
        num_threads=4,
        sample_rate=16000,
        feature_dim=80,
        decoding_method="greedy_search",
        provider="cpu",
        enable_endpoint_detection=True,
        rule1_min_trailing_silence=2.4,
        rule2_min_trailing_silence=1.2,
        rule3_min_utterance_length=300,
    )

    return recognizer


def get_audio_device_info():
    import sounddevice as sd

    default_device = sd.query_devices(kind='input')
    device_name = default_device['name']
    native_rate = int(default_device['default_samplerate'])
    hostapi_idx = default_device['hostapi']
    hostapi_name = sd.query_hostapis(hostapi_idx)['name']

    return {
        'name': device_name,
        'native_rate': native_rate,
        'hostapi': hostapi_name,
    }


def run_streaming_demo(recognizer):
    import sounddevice as sd
    import soxr

    device_info = get_audio_device_info()
    recording_rate = device_info['native_rate']
    chunk_size_native = int(CHUNK_SIZE * recording_rate / SHERPA_SAMPLE_RATE)

    print(f"Audio: {device_info['name']} ({recording_rate} Hz)")

    stream = recognizer.create_stream()
    last_text = ""
    segment_count = 0

    def audio_callback(indata, frames, time_info, status):
        samples = indata[:, 0].astype(np.float32)
        samples = soxr.resample(samples, recording_rate, SHERPA_SAMPLE_RATE).astype(np.float32)
        stream.accept_waveform(SHERPA_SAMPLE_RATE, samples)

    print("\n" + "=" * 50)
    print("Speak now. Press Ctrl+C to stop.")
    print("=" * 50 + "\n")

    try:
        with sd.InputStream(
            samplerate=recording_rate,
            channels=1,
            dtype=np.float32,
            blocksize=chunk_size_native,
            callback=audio_callback,
        ):
            while True:
                while recognizer.is_ready(stream):
                    recognizer.decode_stream(stream)

                text = recognizer.get_result(stream).strip()

                if text and text != last_text:
                    display_text = text if len(text) < 70 else "..." + text[-67:]
                    print(f"\r{display_text:<70}", end="", flush=True)
                    last_text = text

                if recognizer.is_endpoint(stream):
                    if text:
                        segment_count += 1
                        print(f"\r[{segment_count}] {text:<66}")
                        last_text = ""
                    recognizer.reset(stream)

                time.sleep(0.02)

    except KeyboardInterrupt:
        print("\n")

    print(f"Recognized {segment_count} utterance(s)")


def main():
    model_type = "standard"
    if "--ort" in sys.argv:
        model_type = "ort"

    print(f"Sherpa-ONNX Streaming Demo [{model_type.upper()}]")

    result = get_model_path(model_type)
    if not result:
        if model_type == "ort":
            print("Download: huggingface-cli download bookbot/sherpa-onnx-ort-streaming-zipformer-en-2023-06-26")
        else:
            print("Download: huggingface-cli download csukuangfj/sherpa-onnx-streaming-zipformer-en-20M-2023-02-17")
        sys.exit(1)

    model_path, model_info = result

    print("Loading model...", end=" ", flush=True)
    t0 = time.time()
    recognizer = create_recognizer(model_path, model_info)
    if not recognizer:
        sys.exit(1)
    print(f"done ({time.time() - t0:.2f}s)")

    run_streaming_demo(recognizer)


if __name__ == "__main__":
    main()
