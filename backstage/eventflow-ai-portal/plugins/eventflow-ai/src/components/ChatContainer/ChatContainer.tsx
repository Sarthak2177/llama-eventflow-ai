import React, { useEffect, useRef } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import { MessageBubble } from '../MessageBubble/MessageBubble';
import { Message } from '../ChatPage/ChatPage';

const useStyles = makeStyles(theme => ({
  container: {
    flexGrow: 1,
    overflowY: 'auto',
    padding: '20px 5px 20px 20px',
    display: 'flex',
    flexDirection: 'column',
    gap: '0px',
    backgroundColor: '#ffffff',
    borderRadius: '12px',
    border: '1px solid #d9e2ec',
    boxShadow: '0 2px 8px rgba(16,42,67,.05)',
    marginBottom: theme.spacing(2),
  },
  typingIndicator: {
    alignSelf: 'flex-start',
    backgroundColor: theme.palette.background.paper,
    padding: theme.spacing(2),
    borderRadius: theme.shape.borderRadius,
    color: theme.palette.text.secondary,
    fontStyle: 'italic',
    boxShadow: theme.shadows[1],
  },
}));

type ChatContainerProps = {
  messages: Message[];
  isTyping: boolean;
};

export const ChatContainer = ({ messages, isTyping }: ChatContainerProps) => {
  const classes = useStyles();
  const endOfMessagesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isTyping]);

  return (
    <div className={classes.container}>
      {messages.map(msg => (
        <MessageBubble key={msg.id} role={msg.role} text={msg.text} />
      ))}
      
      {isTyping && (
        <div className={classes.typingIndicator}>
          AI is thinking...
        </div>
      )}
      <div ref={endOfMessagesRef} />
    </div>
  );
};
