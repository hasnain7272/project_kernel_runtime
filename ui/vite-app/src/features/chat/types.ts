export type ChatRole = 'user' | 'assistant' | 'tool' | 'system';

export interface ToolCall {
  function?: {
    name?: string;
    arguments?: string;
  };
  status?: string;
}

export interface Msg {
  role: ChatRole;
  content: string;
  streaming?: boolean;
  tool_calls?: ToolCall[];
}
