import { useState, useEffect } from 'react';
import { useApi, discoveryApiRef, fetchApiRef } from '@backstage/core-plugin-api';
import { Page, Header, Content } from '@backstage/core-components';
import { makeStyles } from '@material-ui/core/styles';
import { ChatContainer } from '../ChatContainer/ChatContainer';
import { ChatInput } from '../ChatInput/ChatInput';

const useStyles = makeStyles(theme => ({
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    maxHeight: 'calc(100vh - 160px)',
    maxWidth: '1300px',
    width: '100%',
    margin: '0 auto',
    padding: '28px',
    backgroundColor: '#f5f8fb',
    borderRadius: '12px',
  },
}));

export type Message = {
  id: string;
  role: 'user' | 'ai';
  text: string;
};

export const ChatPage = () => {
  const classes = useStyles();
  const discoveryApi = useApi(discoveryApiRef);
  const fetchApi = useApi(fetchApiRef);
  
  const [messages, setMessages] = useState<Message[]>([
    {
      id: 'welcome-1',
      role: 'ai',
      text: 'Hello! I am EventFlow AI, your intelligent assistant for Solace Event API Products. How can I help you today?',
    }
  ]);
  const [isTyping, setIsTyping] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize session on mount
  useEffect(() => {
    let mounted = true;
    const initSession = async () => {
      try {
        const proxyUrl = await discoveryApi.getBaseUrl('proxy');
        const response = await fetchApi.fetch(`${proxyUrl}/eventflow-api/session`, {
          method: 'POST',
        });
        if (response.ok && mounted) {
          const data = await response.json();
          setSessionId(data.session_id);
        }
      } catch (error) {
        console.error('Failed to initialize session:', error);
      }
    };
    initSession();
    return () => { mounted = false; };
  }, [discoveryApi, fetchApi]);

  const handleSendMessage = async (text: string) => {
    if (!text.trim()) return;

    // Add user message
    const userMsg: Message = { id: Date.now().toString(), role: 'user', text };
    setMessages(prev => [...prev, userMsg]);
    setIsTyping(true);

    try {
      const proxyUrl = await discoveryApi.getBaseUrl('proxy');
      const response = await fetchApi.fetch(`${proxyUrl}/eventflow-api/chat`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message: text,
          session_id: sessionId,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        const aiMsg: Message = {
          id: (Date.now() + 1).toString(),
          role: 'ai',
          text: data.reply || 'Sorry, I received an empty response.',
        };
        setMessages(prev => [...prev, aiMsg]);
      } else {
        throw new Error(`Server returned status: ${response.status}`);
      }
    } catch (error) {
      console.error('Chat error:', error);
      const errorMsg: Message = {
        id: (Date.now() + 1).toString(),
        role: 'ai',
        text: `Error connecting to EventFlow AI backend. Please ensure the Python server is running on port 8000.`,
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setIsTyping(false);
    }
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
