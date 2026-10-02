import { useState } from 'react';
import { makeStyles } from '@material-ui/core/styles';
import { TextField, IconButton, Paper } from '@material-ui/core';
import SendIcon from '@material-ui/icons/Send';

const useStyles = makeStyles(theme => ({
  inputContainer: {
    display: 'flex',
    padding: theme.spacing(2),
    gap: `${theme.spacing(2)}px`,
    alignItems: 'center',
    backgroundColor: theme.palette.background.paper,
    borderRadius: theme.shape.borderRadius,
    boxShadow: theme.shadows[2],
  },
  textField: {
    flexGrow: 1,
  },
  sendButton: {
    color: theme.palette.primary.main,
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

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Paper className={classes.inputContainer}>
      <TextField
        className={classes.textField}
        variant="outlined"
        placeholder="Ask EventFlow AI a question about your Solace Event APIs..."
        value={text}
        onChange={e => setText(e.target.value)}
        onKeyPress={handleKeyPress}
        disabled={disabled}
        multiline
        maxRows={4}
        size="small"
      />
      <IconButton 
        className={classes.sendButton} 
        onClick={handleSend} 
        disabled={!text.trim() || disabled}
      >
        <SendIcon />
      </IconButton>
    </Paper>
  );
};
