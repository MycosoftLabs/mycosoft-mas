"use client";

import { Search } from "lucide-react";
import { useState } from "react";

export function SearchBar() {
  const [searchQuery, setSearchQuery] = useState("");

  return (
    <div className="flex items-center gap-2 rounded-lg bg-[#0F172A] px-3 py-2">
      <Search className="h-4 w-4 text-gray-400" />
      <input
        type="text"
        placeholder="Search entities..."
        value={searchQuery}
        onChange={(e) => setSearchQuery(e.target.value)}
        className="bg-transparent text-sm outline-none placeholder:text-gray-500"
      />
    </div>
  );
}
