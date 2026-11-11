#!/usr/bin/env python3
"""Original local-only speech candidates; never invent human review."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import wave
import lameenc
from content_source import transcript

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / ".local/phase10e/samples"
RATE = 22050
TEXTS = {
    "a": [
        "A small lamp stands beside the window.", "Nora opens the repair room at nine.",
        "She places a notebook on the table.", "A neighbor brings a broken clock.",
        "Please put the clock beside the lamp.", "We can look at it together.",
        "The clock needs a new battery.", "Nora checks the label before she starts.",
        "Her neighbor holds the small cover.", "They hear a quiet tick at last.",
        "The neighbor writes the date in the notebook.", "A simple repair can save a useful thing.",
    ],
    "b": [
        "Our class meets beside the river.", "We carry light bags for the short walk.",
        "A wooden bank sign points toward the town.", "The river bank is covered with grass.",
        "Jon takes a photograph of the old bridge.", "A teacher asks us to count the arches.",
        "We find three arches above the water.", "The middle arch is wider than the others.",
        "Please stand beside the stone wall.", "The path is narrow near the bridge.",
        "We let a cyclist pass before we move.", "Jon notices a bird under the arch.",
        "The bird carries a thin piece of grass.", "It is building a nest above the water.",
        "We watch quietly from the path.", "Nobody reaches toward the nest.",
        "After lunch we visit a small bank.", "Jon asks about saving money for a bicycle.",
        "A worker gives him a simple leaflet.", "He reads the numbers with his teacher.",
        "The river bank and the savings bank are different places.",
        "The same word can have different meanings.", "We write two examples in our notebooks.",
        "Then we walk back beside the river.",
    ],
}


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()


def speech(directory, index, text):
    aiff = directory / f"{index}.aiff"
    wav = directory / f"{index}.wav"
    subprocess.run(["/usr/bin/say", "-v", "Samantha", "-r", "170", "-o", str(aiff), text], check=True, timeout=60)
    subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", f"LEI16@{RATE}", "-c", "1", str(aiff), str(wav)], check=True, timeout=60)
    with wave.open(str(wav)) as reader:
        return reader.readframes(reader.getnframes())


def encode(path, pcm):
    encoder = lameenc.Encoder()
    encoder.set_bit_rate(64)
    encoder.set_in_sample_rate(RATE)
    encoder.set_channels(1)
    encoder.set_quality(2)
    raw = encoder.encode(pcm) + encoder.flush()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(raw)
    decoded = path.with_suffix(".wav")
    subprocess.run(["/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16", str(path), str(decoded)], check=True, timeout=60)
    with wave.open(str(decoded)) as reader:
        duration = reader.getnframes() * 1000 // reader.getframerate()
    return raw, duration


def generate(name, texts):
    directory = OUT / name
    directory.mkdir(parents=True, exist_ok=True)
    work = OUT / (name + "-work")
    work.mkdir(exist_ok=True)
    version = f"sample-{name}-v1"
    transcript_text = "\n".join(texts) + "\n"
    source_ref = f"{version}-source.txt"
    (directory / source_ref).write_text(transcript_text)
    source = {"id": version + "-text-license", "medium": "text", "sourceType": "original",
              "sourceRef": source_ref, "sha256": sha(transcript_text.encode()), "rightsScope": "local_test_only",
              "reviewStatus": "pending_review", "proofRef": "Phase10E original engineering text; not a textbook",
              "reviewer": None, "reviewedAt": TIMESTAMP}
    sources = [source]
    paragraphs = [{"id": f"{version}-p{index}", "stableKey": f"paragraph-{index}", "sequence": index,
                   "sourceRef": source_ref} for index in range(1, (2 if name == "a" else 3) + 1)]
    clips = [speech(work, index, text) for index, text in enumerate(texts, 1)]
    assets, sentences = [], []
    groups = [list(range(len(texts)))] if name == "a" else [[index] for index in range(len(texts))]
    for number, group in enumerate(groups, 1):
        key = f"media/{version}/{number}.mp3"
        silence = bytes(RATE // 4 * 2)
        pcm = b"".join(clips[index] + silence for index in group)
        raw, duration = encode(directory / key, pcm)
        audio_id = f"{version}-a{number}"
        license_id = f"{version}-al{number}"
        sources.append({"id": license_id, "medium": "audio", "sourceType": "original", "sourceRef": key,
            "sha256": sha(raw), "rightsScope": "local_test_only", "reviewStatus": "pending_review",
            "proofRef": "macOS SLA section 2.F; local personal non-commercial use only; redistribution not authorized",
            "reviewer": None, "reviewedAt": TIMESTAMP})
        asset = {"id": audio_id, "licenseId": license_id, "sourceKind": "original_tts", "storageKey": key,
            "mimeType": "audio/mpeg", "byteSize": len(raw), "durationMs": duration, "sha256": sha(raw),
            "alignment": {"status": "needs_review", "method": "concatenated-source-pcm-candidate",
                "audioSha256": sha(raw), "transcriptSha256": sha(transcript([texts[index] for index in group])),
                "transcriptNormalization": "transcript-v1", "sentenceIds": [f"{version}-s{index+1}" for index in group],
                "reviewer": None, "reviewedAt": None}}
        assets.append(asset)
        position = 0
        for index in group:
            length = len(clips[index]) * 1000 // (RATE * 2)
            sentences.append({"id": f"{version}-s{index+1}", "stableKey": f"sentence-{index+1}",
                "paragraphId": f"{version}-p{index // (6 if name == 'a' else 8)+1}", "sequence": index+1,
                "speaker": "Narrator", "text": texts[index], "translation": "", "explanation": "本地预置讲解",
                "focus": "beside", "audioAssetId": audio_id, "startMs": position,
                "endMs": min(position + length, duration)})
            position += length + 250
    knowledge = [{"conceptId": "sample-beside-location", "occurrenceId": f"{version}-beside", "kind": "vocabulary",
        "canonicalKey": "beside", "senseKey": "next-to", "term": "beside", "meaning": "在旁边", "sentenceId": f"{version}-s1"}]
    if name == "b":
        knowledge.extend([{"conceptId": "sample-bank-" + sense, "occurrenceId": f"{version}-bank-{sense}",
            "kind": "vocabulary", "canonicalKey": "bank", "senseKey": sense, "term": "bank", "meaning": meaning,
            "sentenceId": f"{version}-s{index}"} for sense, meaning, index in [("river-edge", "河岸", 4), ("finance", "银行", 17)]])
    exercises = [{"id": sentence["id"] + "-dictation", "kind": "dictation", "sentenceIds": [sentence["id"]],
                  "occurrenceIds": [], "prompt": "Listen and write.", "options": [], "answerKey": None,
                  "explanation": ""} for sentence in sentences]
    for index in range(1, (5 if name == "a" else 12) + 2):
        identifier = f"{version}-q{index}"
        exercises.append({"id": identifier, "kind": "reading_choice" if index == 1 else "quiz_choice",
            "sentenceIds": [f"{version}-s1"], "occurrenceIds": [f"{version}-beside"],
            "prompt": "What does beside mean in the first sentence?",
            "options": [{"id": identifier + "-a", "text": "Next to"}, {"id": identifier + "-b", "text": "Far from"}],
            "answerKey": identifier + "-a", "explanation": "Beside describes a position next to another place or object."})
    content = {"schemaVersion": "northstar.content.core.v1", "packageId": version + "-package", "book": None,
        "lesson": {"id": "sample-" + name, "slug": "sample-" + name, "title": "The Repair Room" if name == "a" else "A Walk Beside the River",
                   "sequence": 1 if name == "a" else 2, "kind": "original"},
        "version": {"id": version, "number": 1, "licenseId": source["id"], "transcriptSha256": sha(transcript(texts)),
                    "transcriptNormalization": "transcript-v1", "contentReadiness": "basic_content"},
        "sources": sources, "paragraphs": paragraphs, "sentences": sentences, "audioAssets": assets,
        "knowledge": knowledge, "exercises": exercises,
        "exerciseSets": [{"id": version + "-quiz", "purpose": "practice", "protocolVersion": "quiz_choice_v1",
                         "contextGroupId": version, "exerciseIds": [item["id"] for item in exercises if item["kind"] == "quiz_choice"]}]}
    if name == "a":
        content["fullAudioAssetId"] = assets[0]["id"]
    raw = canonical(content)
    (directory / "package.json").write_bytes(raw)
    manifest = {"packageId": content["packageId"], "normalization": "northstar.json.sorted.v1",
        "rawSha256": sha(raw), "contentSha256": sha(raw),
        "sourceInventory": {item["id"]: {"sha256": item["sha256"], "originalFilename": Path(item["sourceRef"]).name,
            "byteSize": (directory / item["sourceRef"]).stat().st_size, "createdAt": TIMESTAMP,
            "reviewedAt": TIMESTAMP, "expiresAt": None} for item in sources},
        "proofreading": {"rawTranscript": transcript_text, "correctedTranscript": transcript_text,
            "sourceSha256": source["sha256"], "correctedSha256": sha(transcript_text.encode()),
            "status": "unreviewed", "revision": 0, "reviewer": None, "reviewedAt": None, "audit": []}}
    (directory / "manifest.json").write_bytes(canonical(manifest))
    print(json.dumps({"sample": name, "sentences": len(sentences), "assets": len(assets),
                      "humanReview": "NOT VERIFIED", "root": str(directory)}), flush=True)



if __name__ == "__main__":
    TIMESTAMP = "2026-11-05T00:00:00Z"
    for name in sys.argv[1:] or ["a", "b"]:
        generate(name, TEXTS[name])
