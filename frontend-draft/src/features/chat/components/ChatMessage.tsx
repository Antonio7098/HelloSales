import { cn } from "@/shared/lib/cn";

type ChatMessageProps = {
  role: "user" | "assistant";
  content: string;
  streaming?: boolean;
  timestamp?: string;
};

const roleLabel: Record<ChatMessageProps["role"], string> = {
  user: "You",
  assistant: "Analyst",
};

export function ChatMessage({ role, content, streaming = false, timestamp }: ChatMessageProps) {
  return (
    <div
      className={cn(
        "msg",
        role === "user" ? "msg--user" : "msg--assistant",
        streaming && "msg--streaming",
      )}
    >
      <div className="msg-role">
        <span>{roleLabel[role]}</span>
        {timestamp ? <span>· {timestamp}</span> : null}
      </div>
      <div className="msg-bubble">{content || (streaming ? "" : " ")}</div>
    </div>
  );
}
