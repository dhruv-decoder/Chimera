"use client";
import { useState } from "react";
import { Story } from "@/components/story/Story";
import { Console } from "@/components/console/Console";

export default function Page() {
  const [mode, setMode] = useState<"story" | "console">("story");
  const [entry, setEntry] = useState("overview");

  return mode === "story" ? (
    <Story
      onLaunch={(view = "overview") => {
        setEntry(view);
        setMode("console");
      }}
    />
  ) : (
    <Console initial={entry} onExit={() => setMode("story")} />
  );
}
