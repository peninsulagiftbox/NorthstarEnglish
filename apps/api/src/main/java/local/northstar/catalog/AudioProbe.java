package local.northstar.catalog;

import java.io.IOException;
import java.io.RandomAccessFile;
import java.nio.file.*;
import java.util.*;
import java.util.concurrent.TimeUnit;

/** Local macOS decoder. Missing decoder fails closed; metadata/hash alone never prove decoding. */
final class AudioProbe {
    private static final Map<String, Long> CACHE = new LinkedHashMap<>();
    static synchronized long duration(Path path, String hash) throws IOException {
        var attrs = Files.readAttributes(path, java.nio.file.attribute.BasicFileAttributes.class);
        String key = path.toRealPath()+":"+hash+":"+attrs.fileKey()+":"+attrs.size()+":"+attrs.lastModifiedTime();
        Long previous = CACHE.get(key); if (previous != null) return previous;
        try (var input = Files.newInputStream(path)) {
            byte[] header = input.readNBytes(3);
            if (header.length < 3 || !((header[0]=='I' && header[1]=='D' && header[2]=='3')
                    || ((header[0]&255)==255 && (header[1]&224)==224))) throw new IOException("Not MPEG audio");
        }
        if (!Files.isExecutable(Path.of("/usr/bin/afconvert"))) throw new IOException("Local audio decoder unavailable");
        Path pcm = Files.createTempFile("northstar-audio-", ".wav");
        Process process = null;
        try {
            process = new ProcessBuilder("/usr/bin/afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", path.toString(), pcm.toString())
                    .redirectOutput(ProcessBuilder.Redirect.DISCARD).redirectError(ProcessBuilder.Redirect.DISCARD).start();
            if (!process.waitFor(60, TimeUnit.SECONDS) || process.exitValue()!=0) throw new IOException("Audio decode failed");
            long duration = waveDuration(pcm);
            if (duration<=0) throw new IOException("Empty decoded audio");
            if (CACHE.size()>=64) CACHE.clear();
            CACHE.put(key,duration); return duration;
        } catch (InterruptedException error) { Thread.currentThread().interrupt(); throw new IOException("Audio decode interrupted",error); }
        finally { if(process!=null && process.isAlive())process.destroyForcibly(); Files.deleteIfExists(pcm); }
    }
    private static long unsignedInt(RandomAccessFile file) throws IOException { return Integer.toUnsignedLong(Integer.reverseBytes(file.readInt())); }
    private static long waveDuration(Path path) throws IOException {
        try(var file=new RandomAccessFile(path.toFile(),"r")) {
            if(file.readInt()!=0x52494646)throw new IOException("Invalid decoded WAVE");
            unsignedInt(file);if(file.readInt()!=0x57415645)throw new IOException("Invalid decoded WAVE");
            long byteRate=0;
            while(file.getFilePointer()+8<=file.length()) {
                int chunk=file.readInt();long size=unsignedInt(file),start=file.getFilePointer();
                if(size>file.length()-start)throw new IOException("Truncated decoded audio");
                if(chunk==0x666d7420 && size>=16){file.skipBytes(8);byteRate=unsignedInt(file);}
                if(chunk==0x64617461 && byteRate>0)return size*1000/byteRate;
                file.seek(start+size+(size%2));
            }
            throw new IOException("Decoded audio has no samples");
        }
    }
}
