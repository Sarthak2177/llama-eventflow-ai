import { useState, useRef, useEffect } from 'react';
import { Page, Header, Content } from '@backstage/core-components';
import { makeStyles } from '@material-ui/core/styles';
import { ChatContainer } from '../ChatContainer/ChatContainer';
import { ChatInput } from '../ChatInput/ChatInput';

const useStyles = makeStyles(theme => ({
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    maxHeight: 'calc(100vh - 160px)', // Adjust based on header size
  },
}));

export type Message = {
  id: string;
  role: 'user' | 'ai';
  text: string;
};

export const ChatPage = () => {
  const classes = useStyles();
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-1',
      role: 'ai',
      text: 'Hello! I am EventFlow AI, your intelligent assistant for Solace Event API Products. How can I help you today?',
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);

  const handleSendMessage = (text: string) => {
    if (!text.trim()) return;

    // Add user message
    const userMsg: Message = { id: Date.now().toString(), role: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    // Mock AI response
    setTimeout(() => {
      const aiMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: `This is a mock response to: "${text}". Once connected to the backend, I will process this using LangGraph and Solace MCP.`,
      };
      setMessages(prev => [...prev, aiMsg]);
      setIsTyping(false);
    }, 1500);
  };

  return (
    <Page themeId="tool">
      <Header title="EventFlow AI" subtitle="Intelligent assistant for your Event API Products" />
      <Content>
        <div className={classes.container}>
          <ChatContainer messages={messages} isTyping={isTyping} />
          <ChatInput onSend={handleSendMessage} disabled={isTyping} />
        </div>
      </Content>
    </Page>
  );
};
