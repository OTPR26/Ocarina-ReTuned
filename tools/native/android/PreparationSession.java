// SPDX-License-Identifier: GPL-2.0-or-later
package org.triaevum.android;

import java.io.File;
import java.io.IOException;
import java.nio.channels.FileChannel;
import java.nio.channels.FileLock;
import java.nio.channels.OverlappingFileLockException;
import java.nio.file.Files;
import java.nio.file.StandardOpenOption;

/** The OS releases this lock if either isolated worker process is killed. */
final class PreparationSession implements AutoCloseable {
    private final FileChannel channel;
    private final FileLock lock;
    private PreparationSession(FileChannel channel, FileLock lock) { this.channel=channel; this.lock=lock; }
    static PreparationSession acquire(File directory) throws IOException {
        if(!directory.isDirectory()&&!directory.mkdirs())throw new IOException("Game storage is unavailable");
        File file=new File(directory,".preparation-session.lock");
        if(Files.isSymbolicLink(file.toPath()))throw new IOException("Invalid preparation session file");
        FileChannel channel=FileChannel.open(file.toPath(),StandardOpenOption.CREATE,StandardOpenOption.WRITE);
        try {
            FileLock lock=channel.tryLock();
            if(lock==null)throw new IOException("Another game preparation or model import is running");
            return new PreparationSession(channel,lock);
        } catch(OverlappingFileLockException error) {
            channel.close(); throw new IOException("Another game preparation or model import is running");
        } catch(IOException | RuntimeException error) { channel.close(); throw error; }
    }
    @Override public void close() throws IOException {
        try { lock.release(); } finally { channel.close(); }
    }
}
