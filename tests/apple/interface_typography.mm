#include <CoreText/CoreText.h>
#include <Foundation/Foundation.h>
#include <cassert>
#include "../../tools/frontend/startup_layout.h"

int main(int argc, char** argv) {
    @autoreleasepool {
        assert(argc == 2);
        NSString* path = [NSString stringWithUTF8String:argv[1]];
        CGDataProviderRef data = CGDataProviderCreateWithFilename(path.UTF8String);
        CGFontRef face = CGFontCreateWithDataProvider(data);
        assert(face);
        for (auto size : {std::pair{320.f,568.f}, {568.f,320.f}, {852.f,393.f}, {1280.f,720.f}}) {
            CTFontRef baseFont = CTFontCreateWithGraphicsFont(face,20,nullptr,nullptr);
            NSDictionary* baseAttributes = @{(__bridge NSString*)kCTFontAttributeName:(__bridge id)baseFont};
            NSAttributedString* baseText = [[NSAttributedString alloc] initWithString:@"Start game" attributes:baseAttributes];
            CTLineRef baseLine = CTLineCreateWithAttributedString((__bridge CFAttributedStringRef)baseText);
            const double labelWidth = CTLineGetTypographicBounds(baseLine,nullptr,nullptr,nullptr);
            const auto menu = RetunedFrontend::StartupLayout(size.first,size.second,1,20,true,true,labelWidth);
            CFRelease(baseLine); CFRelease(baseFont);
            CTFontRef font = CTFontCreateWithGraphicsFont(face,20*menu.TextScale,nullptr,nullptr);
            for (NSString* label in @[@"Start game", @"Settings", @"About"]) {
                NSDictionary* attributes = @{(__bridge NSString*)kCTFontAttributeName:(__bridge id)font};
                NSAttributedString* text = [[NSAttributedString alloc] initWithString:label attributes:attributes];
                CTLineRef line = CTLineCreateWithAttributedString((__bridge CFAttributedStringRef)text);
                const double width = CTLineGetTypographicBounds(line,nullptr,nullptr,nullptr);
                assert(width + 24 <= menu.Width + .01);
                assert(20*menu.TextScale + 12 <= menu.Height);
                CFRelease(line);
            }
            CFRelease(font);
        }
        CGFontRelease(face);
        CGDataProviderRelease(data);
    }
}
