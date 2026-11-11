import AppKit
import PDFKit

let directory = URL(fileURLWithPath: CommandLine.arguments[1])
try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
let text = "Original Northstar test material.\nNora repairs a small clock beside the window.\nThe clock needs a new battery."
let pageSize = NSRect(x: 0, y: 0, width: 612, height: 792)
func drawText() {
    (text as NSString).draw(in: NSRect(x: 50, y: 550, width: 500, height: 190),
        withAttributes: [.font: NSFont.systemFont(ofSize: 18), .foregroundColor: NSColor.black])
}
let image = NSImage(size: pageSize.size)
image.lockFocus()
NSColor.white.setFill()
pageSize.fill()
drawText()
image.unlockFocus()
guard let bitmap = NSBitmapImageRep(data: image.tiffRepresentation!), let cgImage = bitmap.cgImage else { exit(2) }
try bitmap.representation(using: .png, properties: [:])!.write(to: directory.appendingPathComponent("scan.png"))
for scanned in [false, true] {
    let url = directory.appendingPathComponent(scanned ? "scan.pdf" : "text.pdf")
    var box = pageSize
    guard let context = CGContext(url as CFURL, mediaBox: &box, nil) else { exit(2) }
    context.beginPDFPage(nil)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(cgContext: context, flipped: false)
    if scanned { context.draw(cgImage, in: pageSize) } else { drawText() }
    NSGraphicsContext.restoreGraphicsState()
    context.endPDFPage()
    context.closePDF()
}
let document = PDFDocument(url: directory.appendingPathComponent("text.pdf"))!
document.write(to: directory.appendingPathComponent("encrypted.pdf"),
    withOptions: [.ownerPasswordOption: "fixture-only", .userPasswordOption: "fixture-only"])
let longDocument = PDFDocument()
for index in 0..<201 {
    longDocument.insert(PDFPage(image: image)!, at: index)
}
longDocument.write(to: directory.appendingPathComponent("over-limit.pdf"))
try text.write(to: directory.appendingPathComponent("original.txt"), atomically: false, encoding: .utf8)
