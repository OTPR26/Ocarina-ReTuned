#!/usr/bin/env swift

import AppKit
import Foundation

guard CommandLine.arguments.count == 4 else {
    fputs("usage: generate_tvos_icon.swift <icon.png> <background.png> <AppIconTV.brandassets>\n",
          stderr)
    exit(2)
}

let iconURL = URL(fileURLWithPath: CommandLine.arguments[1])
let backgroundURL = URL(fileURLWithPath: CommandLine.arguments[2])
let catalogURL = URL(fileURLWithPath: CommandLine.arguments[3])

guard let icon = NSImage(contentsOf: iconURL),
      let background = NSImage(contentsOf: backgroundURL) else {
    fputs("Unable to load the OcarinaReTuned icon source images.\n", stderr)
    exit(1)
}

func render(width: Int, height: Int, foreground: Bool, output: URL) throws {
    guard let bitmap = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: width,
        pixelsHigh: height,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    ) else {
        throw NSError(domain: "OcarinaReTunedIcon", code: 1)
    }

    bitmap.size = NSSize(width: width, height: height)
    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: bitmap)
    NSGraphicsContext.current?.imageInterpolation = .high
    NSColor.clear.set()
    NSRect(x: 0, y: 0, width: width, height: height).fill()

    if foreground {
        let side = CGFloat(height) * 0.82
        let destination = NSRect(
            x: (CGFloat(width) - side) / 2,
            y: (CGFloat(height) - side) / 2,
            width: side,
            height: side
        )
        icon.draw(in: destination, from: .zero, operation: .sourceOver, fraction: 1)
    } else {
        NSColor(srgbRed: 0.015, green: 0.035, blue: 0.09, alpha: 1).set()
        NSRect(x: 0, y: 0, width: width, height: height).fill()
    }

    NSGraphicsContext.restoreGraphicsState()
    guard let png = bitmap.representation(using: .png, properties: [:]) else {
        throw NSError(domain: "OcarinaReTunedIcon", code: 2)
    }
    try png.write(to: output, options: .atomic)
}

let large = catalogURL.appendingPathComponent("App Icon - Large.imagestack")
let small = catalogURL.appendingPathComponent("App Icon - Small.imagestack")
let largeForeground = large.appendingPathComponent(
    "Foreground.imagestacklayer/Content.imageset/Foreground.png")
let largeBackground = large.appendingPathComponent(
    "Background.imagestacklayer/Content.imageset/Background.png")
let smallForeground = small.appendingPathComponent(
    "Foreground.imagestacklayer/Content.imageset/Foreground.png")
let smallForeground2x = small.appendingPathComponent(
    "Foreground.imagestacklayer/Content.imageset/Foreground@2x.png")
let smallBackground = small.appendingPathComponent(
    "Background.imagestacklayer/Content.imageset/Background.png")
let smallBackground2x = small.appendingPathComponent(
    "Background.imagestacklayer/Content.imageset/Background@2x.png")

do {
    try render(width: 1280, height: 768, foreground: true, output: largeForeground)
    try render(width: 1280, height: 768, foreground: false, output: largeBackground)
    try render(width: 400, height: 240, foreground: true, output: smallForeground)
    try render(width: 800, height: 480, foreground: true, output: smallForeground2x)
    try render(width: 400, height: 240, foreground: false, output: smallBackground)
    try render(width: 800, height: 480, foreground: false, output: smallBackground2x)
} catch {
    fputs("Unable to generate tvOS icon layers: \(error)\n", stderr)
    exit(1)
}
