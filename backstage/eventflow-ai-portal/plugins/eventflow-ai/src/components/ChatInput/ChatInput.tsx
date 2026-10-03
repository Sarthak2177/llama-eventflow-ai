import { useState } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import SendIcon from '@material-ui/icons/Send';

const useStyles = makeStyles(theme => ({
  composer: {
    display: 'flex',
    gap: '10px',
    marginTop: '14px',
  },
  input: {
    flex: 1,
    padding: '13px',
    border: '1px solid #b8c7d5',
    borderRadius: '8px',
    fontSize: '14px',
    fontFamily: 'Inter, "Segoe UI", Arial, sans-serif',
    color: '#17324d',
    backgroundColor: '#ffffff',
    outline: 'none',
    '&::placeholder': {
      color: '#627d98',
      opacity: 1,
    },
    '&:focus': {
      borderColor: '#102a43',
    }
  },
  button: {
    border: 0,
    borderRadius: '8px',
    padding: '12px 15px',
    backgroundColor: '#102a43',
    color: '#ffffff',
    fontWeight: 700,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    '&:hover': {
      backgroundColor: '#17324d',
    },
    '&:disabled': {
      backgroundColor: '#627d98',
      cursor: 'not-allowed',
    }
  }
}));

type ChatInputProps = {
  onSend: (text: string) => void;
  disabled: boolean;
};

export const ChatInput = ({ onSend, disabled }: ChatInputProps) => {
  const classes = useStyles();
  const [text, setText] = useState('');

  const handleSend = () => {
    if (text.trim() && !disabled) {
      onSend(text);
      setText('');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={classes.composer}>
      <input
        className={classes.input}
        placeholder="Ask EventFlow AI a question about your Solace Event APIs..."
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyDown={handleKeyPress}
        disabled={disabled}
      />
      <button 
        className={classes.button} 
        onClick={handleSend} 
        disabled={!text.trim() || disabled}
      >
        <SendIcon fontSize="small" />
      </button>
    </div>
  );
};
