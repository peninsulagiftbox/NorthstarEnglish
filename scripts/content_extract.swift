import Foundation
import PDFKit
import Vision
import AppKit

let input = URL(fileURLWithPath: CommandLine.arguments[1])
guard let document = PDFDocument(url: input), !document.isEncrypted,
      document.pageCount > 0, document.pageCount <= 200 else {
    fputs("PDF_INVALID_ENCRYPTED_OR_PAGE_LIMIT\n", stderr)
    exit(2)
}
var pages: [[String: Any]] = []
for index in 0..<document.pageCount {
    guard let page = document.page(at: index) else { exit(2) }
    let text = page.string ?? ""
    var blocks: [[String: Any]] = []
    var method = "PDFKit.text"
    var raw = text
    if text.trimmingCharacters(in: .whitespacesAndNewlines).count < 20 {
        method = "Vision.OCR"
        let image = page.thumbnail(of: NSSize(width: 1600, height: 2200), for: .mediaBox)
        guard let data = image.tiffRepresentation,
              let bitmap = NSBitmapImageRep(data: data),
              let cgImage = bitmap.cgImage else { exit(2) }
        let request = VNRecognizeTextRequest()
        request.recognitionLevel = .accurate
        request.recognitionLanguages = ["en-US"]
        request.usesLanguageCorrection = false
        do {
            try VNImageRequestHandler(cgImage: cgImage).perform([request])
            for observation in request.results ?? [] {
                guard let candidate = observation.topCandidates(1).first else { continue }
                let box = observation.boundingBox
                blocks.append(["text": candidate.string,
                               "box": [box.origin.x, box.origin.y, box.width, box.height]])
            }
            raw = blocks.compactMap { $0["text"] as? String }.joined(separator: "\n")
        } catch {
            pages.append(["page": index + 1, "status": "failed", "method": method,
                          "error": "OCR_FAILED", "rawText": "", "blocks": []])
            continue
        }
    } else {
        for line in page.selection(for: page.bounds(for: .mediaBox))?.selectionsByLine() ?? [] {
            let box = line.bounds(for: page)
            blocks.append(["text": line.string ?? "",
                           "box": [box.origin.x, box.origin.y, box.width, box.height]])
        }
    }
    pages.append(["page": index + 1, "status": "needs_review", "method": method,
                  "rawText": raw, "blocks": blocks,
                  "coordinateSystem": method == "Vision.OCR" ? "normalized_bottom_left" : "pdf_points"])
}
let result: [String: Any] = ["pages": pages, "tool": "PDFKit+Vision",
    "toolVersion": ProcessInfo.processInfo.operatingSystemVersionString,
    "parameters": ["recognitionLevel": "accurate", "languageCorrection": false, "language": "en-US"]]
let output = try JSONSerialization.data(withJSONObject: result, options: [.sortedKeys])
FileHandle.standardOutput.write(output)
