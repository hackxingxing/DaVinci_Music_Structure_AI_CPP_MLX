#import <Cocoa/Cocoa.h>
#import <Foundation/Foundation.h>

#include <cstdlib>
#include <filesystem>
#include <iostream>
#include <string>

struct TaskResult {
    int code = -1;
    std::string output;
};

static NSString *Expand(NSString *path) {
    return [path stringByExpandingTildeInPath];
}

static NSDictionary *ReadJSON(NSString *path, NSError **error) {
    NSData *data = [NSData dataWithContentsOfFile:path options:0 error:error];
    if (!data) return nil;

    id object = [NSJSONSerialization JSONObjectWithData:data options:0 error:error];
    return [object isKindOfClass:[NSDictionary class]] ? object : nil;
}

static BOOL WriteJSON(NSDictionary *dictionary, NSString *path, NSError **error) {
    NSData *data = [NSJSONSerialization dataWithJSONObject:dictionary
                                                   options:NSJSONWritingPrettyPrinted
                                                     error:error];
    return data ? [data writeToFile:path options:NSDataWritingAtomic error:error] : NO;
}

static TaskResult RunTask(NSString *executable, NSArray<NSString *> *arguments) {
    TaskResult result;

    @autoreleasepool {
        NSTask *task = [NSTask new];
        task.executableURL = [NSURL fileURLWithPath:executable];
        task.arguments = arguments;

        NSMutableDictionary *environment = [[[NSProcessInfo processInfo] environment] mutableCopy];
        environment[@"PATH"] = [NSString stringWithFormat:
            @"/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:%@",
            environment[@"PATH"] ?: @""];
        environment[@"PYTHONUNBUFFERED"] = @"1";
        task.environment = environment;

        NSPipe *pipe = [NSPipe pipe];
        task.standardOutput = pipe;
        task.standardError = pipe;

        NSError *launchError = nil;
        if (![task launchAndReturnError:&launchError]) {
            result.code = 127;
            const char *message = [[launchError localizedDescription] UTF8String];
            result.output = std::string(message ? message : "launch failed");
            return result;
        }

        NSData *data = [[pipe fileHandleForReading] readDataToEndOfFile];
        [task waitUntilExit];

        result.code = task.terminationStatus;
        NSString *output = [[NSString alloc] initWithData:data encoding:NSUTF8StringEncoding] ?: @"";
        const char *utf8 = [output UTF8String];
        result.output = std::string(utf8 ? utf8 : "");
    }

    return result;
}

@interface MSAIAppDelegate : NSObject <NSApplicationDelegate>
@property(nonatomic, strong) NSWindow *window;
@property(nonatomic, strong) NSPopUpButton *clipPopup;
@property(nonatomic, strong) NSButton *segments;
@property(nonatomic, strong) NSButton *downbeats;
@property(nonatomic, strong) NSButton *beats;
@property(nonatomic, strong) NSTextField *statusLabel;
@property(nonatomic, strong) NSButton *analyzeButton;
@property(nonatomic, strong) NSDictionary *job;
@property(nonatomic, strong) NSDictionary *config;
@property(nonatomic, strong) NSString *jobPath;
@end

@implementation MSAIAppDelegate

- (BOOL)applicationShouldTerminateAfterLastWindowClosed:(NSApplication *)sender {
    return YES;
}

- (void)applicationDidFinishLaunching:(NSNotification *)notification {
    NSArray *arguments = [[NSProcessInfo processInfo] arguments];
    NSUInteger jobIndex = [arguments indexOfObject:@"--job"];

    if (jobIndex == NSNotFound || jobIndex + 1 >= arguments.count) {
        NSAlert *alert = [NSAlert new];
        alert.messageText = @"Music Structure AI";
        alert.informativeText = @"请从 DaVinci Resolve 的 Workspace → Scripts 启动插件。";
        [alert runModal];
        [NSApp terminate:nil];
        return;
    }

    self.jobPath = arguments[jobIndex + 1];

    NSError *error = nil;
    self.job = ReadJSON(self.jobPath, &error);
    self.config = ReadJSON(
        [Expand(@"~/Library/Application Support/MusicStructureAI_CPP")
            stringByAppendingPathComponent:@"config.json"],
        &error
    );

    if (!self.job || !self.config) {
        NSAlert *alert = [NSAlert new];
        alert.messageText = @"无法读取插件配置";
        alert.informativeText = error.localizedDescription ?: @"请重新运行 install.command";
        [alert runModal];
        [NSApp terminate:nil];
        return;
    }

    [self buildUI];
}

- (NSTextField *)label:(NSString *)text frame:(NSRect)frame {
    NSTextField *label = [[NSTextField alloc] initWithFrame:frame];
    label.stringValue = text;
    label.bezeled = NO;
    label.drawsBackground = NO;
    label.editable = NO;
    label.selectable = NO;
    return label;
}

- (NSButton *)check:(NSString *)title y:(CGFloat)y {
    NSButton *button = [[NSButton alloc] initWithFrame:NSMakeRect(28, y, 640, 26)];
    button.buttonType = NSButtonTypeSwitch;
    button.title = title;
    button.state = NSControlStateValueOn;
    return button;
}

- (void)buildUI {
    self.window = [[NSWindow alloc]
        initWithContentRect:NSMakeRect(0, 0, 720, 430)
                  styleMask:(NSWindowStyleMaskTitled |
                             NSWindowStyleMaskClosable |
                             NSWindowStyleMaskMiniaturizable)
                    backing:NSBackingStoreBuffered
                      defer:NO];
    self.window.title = @"Music Structure AI v0.3.4 · C++ + MLX";
    [self.window center];

    NSView *content = self.window.contentView;

    NSTextField *title = [self label:@"把播放头放到音乐 Clip 内，然后从 Resolve 启动本插件。"
                                 frame:NSMakeRect(28, 385, 660, 24)];
    title.font = [NSFont boldSystemFontOfSize:14];
    [content addSubview:title];

    [content addSubview:[self label:@"播放头音频：" frame:NSMakeRect(28, 340, 95, 26)]];

    self.clipPopup = [[NSPopUpButton alloc] initWithFrame:NSMakeRect(120, 336, 565, 30)
                                                 pullsDown:NO];
    for (NSDictionary *candidate in self.job[@"candidates"]) {
        NSString *displayName = candidate[@"display_name"] ?: candidate[@"name"] ?: @"Audio";
        [self.clipPopup addItemWithTitle:displayName];
    }
    [content addSubview:self.clipPopup];

    self.segments = [self check:@"音乐段落范围：前奏 / 主歌 / 副歌 / 桥段 / 尾奏" y:292];
    [content addSubview:self.segments];

    self.downbeats = [self check:@"小节第一拍（Downbeat / Cyan）" y:258];
    [content addSubview:self.downbeats];

    self.beats = [self check:@"全部节拍（Beat / Blue）" y:224];
    [content addSubview:self.beats];

    NSString *backendText = [NSString stringWithFormat:
        @"后端：Apple MLX · harmonix-all · Python %@（仅负责模型推理）",
        self.config[@"python_version"] ?: @"?"];
    [content addSubview:[self label:backendText frame:NSMakeRect(28, 182, 660, 24)]];

    self.statusLabel = [self label:@"状态：等待分析" frame:NSMakeRect(28, 137, 660, 38)];
    self.statusLabel.maximumNumberOfLines = 2;
    [content addSubview:self.statusLabel];

    self.analyzeButton = [[NSButton alloc] initWithFrame:NSMakeRect(28, 78, 360, 40)];
    self.analyzeButton.title = @"分析并写入 Resolve";
    self.analyzeButton.target = self;
    self.analyzeButton.action = @selector(analyze:);
    [content addSubview:self.analyzeButton];

    NSButton *clearButton = [[NSButton alloc] initWithFrame:NSMakeRect(400, 78, 150, 40)];
    clearButton.title = @"清除插件标记";
    clearButton.target = self;
    clearButton.action = @selector(clearMarkers:);
    [content addSubview:clearButton];

    NSButton *logsButton = [[NSButton alloc] initWithFrame:NSMakeRect(562, 78, 123, 40)];
    logsButton.title = @"打开日志";
    logsButton.target = self;
    logsButton.action = @selector(openLogs:);
    [content addSubview:logsButton];

    NSTextField *footer = [self label:@"自动写回失败时，结果仍会保存；回 Resolve 运行 Apply Last Analysis 即可。"
                                  frame:NSMakeRect(28, 30, 660, 24)];
    footer.textColor = [NSColor secondaryLabelColor];
    [content addSubview:footer];

    [self.window makeKeyAndOrderFront:nil];
    [NSApp activateIgnoringOtherApps:YES];
}

- (void)updateStatus:(NSString *)text {
    dispatch_async(dispatch_get_main_queue(), ^{
        self.statusLabel.stringValue = [@"状态：" stringByAppendingString:(text ?: @"")];
    });
}

- (void)setAnalyzeButtonEnabled:(BOOL)enabled {
    dispatch_async(dispatch_get_main_queue(), ^{
        self.analyzeButton.enabled = enabled;
    });
}

- (void)analyze:(id)sender {
    NSInteger selectedIndex = MAX((NSInteger)0, self.clipPopup.indexOfSelectedItem);
    NSArray *candidates = self.job[@"candidates"];
    if (selectedIndex >= (NSInteger)candidates.count) {
        [self updateStatus:@"没有找到可分析的音频片段。"];
        return;
    }

    NSDictionary *candidate = candidates[selectedIndex];
    NSString *cacheKey = candidate[@"cache_key"] ?: [[NSUUID UUID] UUIDString];
    NSString *cacheDirectory = Expand(@"~/Library/Caches/MusicStructureAI_CPP/analysis");

    NSError *directoryError = nil;
    BOOL directoryOK = [[NSFileManager defaultManager]
        createDirectoryAtPath:cacheDirectory
  withIntermediateDirectories:YES
                   attributes:nil
                        error:&directoryError];
    if (!directoryOK) {
        [self updateStatus:[@"无法创建缓存目录：" stringByAppendingString:
            (directoryError.localizedDescription ?: @"未知错误")]];
        return;
    }

    NSString *analysisPath = [cacheDirectory
        stringByAppendingPathComponent:[cacheKey stringByAppendingString:@".json"]];
    NSString *python = self.config[@"python_executable"];
    NSString *backend = self.config[@"backend_analyzer"];
    NSString *bridge = self.config[@"bridge"];
    NSString *pendingPath = Expand(@"~/Library/Application Support/MusicStructureAI_CPP/pending.json");

    BOOL includeSegments = self.segments.state == NSControlStateValueOn;
    BOOL includeDownbeats = self.downbeats.state == NSControlStateValueOn;
    BOOL includeBeats = self.beats.state == NSControlStateValueOn;

    self.analyzeButton.enabled = NO;
    [self updateStatus:@"正在用 MLX/Metal 分析音乐结构与节拍…"];

    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        TaskResult analyzeResult = RunTask(python, @[
            backend,
            @"--job", self.jobPath,
            @"--candidate-index", [NSString stringWithFormat:@"%ld", (long)selectedIndex],
            @"--output", analysisPath,
            @"--weights-dir", self.config[@"mlx_weights_dir"] ?: Expand(@"~/Library/Application Support/MusicStructureAI_CPP/mlx-weights")
        ]);

        if (analyzeResult.code != 0) {
            NSString *output = [NSString stringWithUTF8String:analyzeResult.output.c_str()] ?: @"";
            [self updateStatus:[@"分析失败：" stringByAppendingString:output]];
            [self setAnalyzeButtonEnabled:YES];
            return;
        }

        NSError *writeError = nil;
        BOOL wrotePending = WriteJSON(@{
            @"job": self.jobPath,
            @"analysis": analysisPath,
            @"candidate_index": @(selectedIndex),
            @"segments": @(includeSegments),
            @"downbeats": @(includeDownbeats),
            @"beats": @(includeBeats),
            @"created_at": @([[NSDate date] timeIntervalSince1970])
        }, pendingPath, &writeError);

        if (!wrotePending) {
            [self updateStatus:[@"分析完成，但保存待写回结果失败：" stringByAppendingString:
                (writeError.localizedDescription ?: @"未知错误")]];
            [self setAnalyzeButtonEnabled:YES];
            return;
        }

        [self updateStatus:@"分析完成，正在写回 Resolve Marker…"];

        TaskResult bridgeResult = RunTask(python, @[
            bridge,
            @"--job", self.jobPath,
            @"--candidate-index", [NSString stringWithFormat:@"%ld", (long)selectedIndex],
            @"--analysis", analysisPath,
            @"--segments", includeSegments ? @"1" : @"0",
            @"--downbeats", includeDownbeats ? @"1" : @"0",
            @"--beats", includeBeats ? @"1" : @"0"
        ]);

        if (bridgeResult.code == 0) {
            NSString *output = [NSString stringWithUTF8String:bridgeResult.output.c_str()] ?: @"";
            [self updateStatus:[@"完成。" stringByAppendingString:output]];
        } else {
            [self updateStatus:@"分析已完成，但外部自动写回失败。回 Resolve 运行 Workspace → Scripts → Utility → MusicStructureAI CPP → Apply Last Analysis 即可写入。"];
        }

        [self setAnalyzeButtonEnabled:YES];
    });
}

- (void)clearMarkers:(id)sender {
    NSInteger selectedIndex = MAX((NSInteger)0, self.clipPopup.indexOfSelectedItem);
    NSString *python = self.config[@"python_executable"];
    NSString *bridge = self.config[@"bridge"];

    [self updateStatus:@"正在清除 Music Structure AI 标记…"];

    dispatch_async(dispatch_get_global_queue(QOS_CLASS_USER_INITIATED, 0), ^{
        TaskResult result = RunTask(python, @[
            bridge,
            @"--job", self.jobPath,
            @"--candidate-index", [NSString stringWithFormat:@"%ld", (long)selectedIndex],
            @"--clear"
        ]);

        if (result.code == 0) {
            [self updateStatus:@"已清除。"];
        } else {
            [self updateStatus:@"外部清除失败。可在 Resolve 运行 Clear Music Structure Markers。"];
        }
    });
}

- (void)openLogs:(id)sender {
    NSString *logDirectory = Expand(@"~/Library/Logs/MusicStructureAI_CPP");
    [[NSFileManager defaultManager] createDirectoryAtPath:logDirectory
                              withIntermediateDirectories:YES
                                               attributes:nil
                                                    error:nil];
    [[NSWorkspace sharedWorkspace] openURL:[NSURL fileURLWithPath:logDirectory]];
}

@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        if (argc >= 2 && std::string(argv[1]) == "--self-test") {
            std::filesystem::path home = std::getenv("HOME") ? std::getenv("HOME") : "";
            std::cout << "MSAI_CPP_SELF_TEST_OK home=" << home.string() << std::endl;
            return 0;
        }

        NSApplication *app = [NSApplication sharedApplication];
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];

        MSAIAppDelegate *delegate = [MSAIAppDelegate new];
        app.delegate = delegate;
        [app run];
    }

    return 0;
}
