#!/usr/bin/env python3
"""
Patch `website/components/devices/mushroom1-details.tsx` to improve mobile video playback:
- Avoid 8K hero video on mobile (swap to smaller source)
- Wire "Watch Film" to open a real MP4 modal
- Support youtube/mp4 in the existing modal
- Add preload="metadata" on background videos

This script performs guarded string replacements (fails fast if expected snippets change).
"""

from __future__ import annotations

from pathlib import Path
import re


def replace_once(s: str, old: str, new: str, *, label: str) -> str:
    if s.count(old) != 1:
        raise SystemExit(f"[FAIL] {label}: expected 1 occurrence, found {s.count(old)}")
    return s.replace(old, new, 1)


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    target = repo_root / "C:\\Users\\admin2\\Desktop\\MYCOSOFT\\CODE\\WEBSITE\\website\\components\\devices\\mushroom1-details.tsx"
    if not target.exists():
        # Fallback when running from workspace root where absolute path isn't valid
        target = repo_root / "components" / "devices" / "mushroom1-details.tsx"

    if not target.exists():
        raise SystemExit(f"[FAIL] Target not found: {target}")

    raw = target.read_bytes()
    # Preserve original line endings
    text = raw.decode("utf-8")

    insert_block = """

interface SelectedVideo {
  kind: "youtube" | "mp4"
  src: string
  title: string
}

function useIsMobile() {
  const [isMobile, setIsMobile] = useState(false)

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 768px)")

    function handleChange() {
      setIsMobile(mediaQuery.matches)
    }

    handleChange()
    mediaQuery.addEventListener("change", handleChange)
    return () => mediaQuery.removeEventListener("change", handleChange)
  }, [])

  return isMobile
}
""".lstrip("\n")

    text = replace_once(
        text,
        '} from "lucide-react"\n\n// Asset configuration',
        f'}} from "lucide-react"\n{insert_block}\n// Asset configuration',
        label="insert SelectedVideo + useIsMobile",
    )

    text = replace_once(
        text,
        "const [selectedVideo, setSelectedVideo] = useState<string | null>(null)",
        "const [selectedVideo, setSelectedVideo] = useState<SelectedVideo | null>(null)",
        label="selectedVideo state type",
    )

    text = replace_once(
        text,
        "const videoRef = useRef<HTMLVideoElement>(null)\n",
        "const videoRef = useRef<HTMLVideoElement>(null)\n  const isMobile = useIsMobile()\n\n  // Mobile reliability: avoid 8K hero playback on phones (can cause videos to stall/fail on iOS)\n  const heroVideoSrc = isMobile ? MUSHROOM1_ASSETS.videos.waterfall : MUSHROOM1_ASSETS.videos.background\n",
        label="add isMobile + heroVideoSrc",
    )

    text = replace_once(
        text,
        "const openVideoModal = (videoId: string) => {\n    setSelectedVideo(videoId)\n    setIsVideoModalOpen(true)\n  }\n",
        'const openVideoModal = (videoId: string) => {\n    setSelectedVideo({ kind: "youtube", src: videoId, title: "Mushroom 1 Video" })\n    setIsVideoModalOpen(true)\n  }\n\n  const openMp4Modal = (videoSrc: string, title: string) => {\n    setSelectedVideo({ kind: "mp4", src: videoSrc, title })\n    setIsVideoModalOpen(true)\n  }\n',
        label="openVideoModal + openMp4Modal",
    )

    text = replace_once(
        text,
        '<source src={MUSHROOM1_ASSETS.videos.background} type="video/mp4" />',
        '<source src={heroVideoSrc} type="video/mp4" />',
        label="hero source swap",
    )

    text = replace_once(
        text,
        '<Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10">',
        '<Button size="lg" variant="outline" className="border-white/30 text-white hover:bg-white/10" onClick={() => openMp4Modal(MUSHROOM1_ASSETS.videos.promo, "Mushroom 1 — Watch Film")}>',
        label="Watch Film onClick",
    )

    # Modal: replace iframe-only with conditional youtube/mp4 rendering.
    text = replace_once(
        text,
        "              <iframe\n                src={`https://www.youtube.com/embed/${selectedVideo}?autoplay=1`}\n                title=\"YouTube video player\"\n                allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\"\n                allowFullScreen\n                className=\"w-full h-full rounded-xl\"\n              />",
        "              {selectedVideo.kind === \"youtube\" ? (\n                <iframe\n                  src={`https://www.youtube.com/embed/${selectedVideo.src}?autoplay=1`}\n                  title={selectedVideo.title}\n                  allow=\"accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture\"\n                  allowFullScreen\n                  className=\"w-full h-full rounded-xl\"\n                />\n              ) : (\n                <video autoPlay controls playsInline className=\"w-full h-full rounded-xl bg-black\">\n                  <source src={selectedVideo.src} type=\"video/mp4\" />\n                </video>\n              )}",
        label="modal iframe -> conditional",
    )

    # Add preload="metadata" to background videos for mobile stability (avoid aggressive full preloads),
    # but only if not already present on the line immediately after `playsInline`.
    text, n = re.subn(
        r"^(\s*)playsInline\s*$\n(?!\1preload=)",
        r"\1playsInline\n\1preload=\"metadata\"\n",
        text,
        flags=re.MULTILINE,
    )
    if n == 0:
        raise SystemExit("[FAIL] preload insertion: expected at least 1 playsInline block")

    target.write_text(text, encoding="utf-8", newline="")
    print(f"[OK] Updated: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

