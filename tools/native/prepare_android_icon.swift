import AppKit
import CoreImage

let source = URL(fileURLWithPath: CommandLine.arguments[1])
let output = URL(fileURLWithPath: CommandLine.arguments[2])
guard let art = CIImage(contentsOf: source) else { fatalError("Cannot read launcher artwork") }
let renderer = CIContext()
for (density, size) in [("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)] {
    // Extend the dark backdrop so the circular crop keeps the mouthpiece and tip.
    let rect = art.extent.insetBy(dx: -art.extent.width * 0.065, dy: -art.extent.height * 0.065)
    guard let expanded = renderer.createCGImage(art.clampedToExtent(), from: rect),
          let canvas = CGContext(data: nil, width: size, height: size, bitsPerComponent: 8,
                                 bytesPerRow: size * 4, space: CGColorSpace(name: CGColorSpace.sRGB)!,
                                 bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue)
    else { fatalError("Cannot render launcher icon") }
    let bounds = CGRect(x: 0, y: 0, width: size, height: size)
    canvas.addEllipse(in: bounds)
    canvas.clip()
    canvas.interpolationQuality = .high
    canvas.draw(expanded, in: bounds)
    let folder = output.appendingPathComponent("mipmap-" + density)
    try FileManager.default.createDirectory(at: folder, withIntermediateDirectories: true)
    let bitmap = NSBitmapImageRep(cgImage: canvas.makeImage()!)
    try bitmap.representation(using: .png, properties: [:])!.write(to: folder.appendingPathComponent("ic_launcher_round.png"))
}
