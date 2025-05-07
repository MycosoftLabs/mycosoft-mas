import * as React from "react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"

interface MycaChatInputProps {
  onSend: (message: string) => void
  isLoading?: boolean
}

export function MycaChatInput({ onSend, isLoading = false }: MycaChatInputProps) {
  const [value, setValue] = React.useState("")

  function handleSend(e: React.FormEvent) {
    e.preventDefault()
    if (value.trim()) {
      onSend(value.trim())
      setValue("")
    }
  }

  return (
    <form className="flex gap-2 w-full" onSubmit={handleSend}>
      <Input
        type="text"
        placeholder="Type a message or command for MYCA..."
        value={value}
        onChange={e => setValue(e.target.value)}
        disabled={isLoading}
        className="flex-1"
      />
      <Button type="submit" disabled={isLoading || !value.trim()}>
        {isLoading ? "Sending..." : "Send"}
      </Button>
    </form>
  )
} 