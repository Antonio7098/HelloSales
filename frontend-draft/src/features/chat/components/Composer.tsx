import { useRef, useState } from "react";
import type { KeyboardEvent } from "react";
import { Button } from "@/design-system/primitives/Button";
import { Textarea } from "@/design-system/primitives/Field";
import { Kbd } from "@/design-system/primitives/Kbd";

type ComposerProps = {
  onSubmit: (text: string) => Promise<void> | void;
  disabled?: boolean;
  busy?: boolean;
  placeholder?: string;
};

export function Composer({
  onSubmit,
  disabled = false,
  busy = false,
  placeholder = "Ask the analyst — for example, “which sections haven't been filled in yet?”",
}: ComposerProps) {
  const [value, setValue] = useState("");
  const ref = useRef<HTMLTextAreaElement | null>(null);

  async function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || disabled || busy) return;
    setValue("");
    try {
      await onSubmit(trimmed);
    } catch {
      setValue(trimmed);
    }
    ref.current?.focus();
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      void handleSubmit();
    }
  }

  return (
    <form
      className="composer"
      onSubmit={(event) => {
        event.preventDefault();
        void handleSubmit();
      }}
    >
      <div className="composer-row">
        <Textarea
          ref={ref}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          rows={1}
          disabled={disabled}
          aria-label="Message"
          autoFocus
        />
        <Button
          type="submit"
          variant="primary"
          disabled={disabled || busy || !value.trim()}
        >
          {busy ? "Sending…" : "Send"}
        </Button>
      </div>
      <div className="composer-hint">
        <span>
          <Kbd>Enter</Kbd> to send · <Kbd>Shift</Kbd>+<Kbd>Enter</Kbd> for newline
        </span>
        <span>Answers are grounded in the governed substrate</span>
      </div>
    </form>
  );
}
