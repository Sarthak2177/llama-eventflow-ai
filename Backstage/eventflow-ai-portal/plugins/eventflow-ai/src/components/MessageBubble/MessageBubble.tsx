import { makeStyles } from '@material-ui/core/styles';
import { Typography, Paper, Avatar } from '@material-ui/core';
import PersonIcon from '@material-ui/icons/Person';
import MemoryIcon from '@material-ui/icons/Memory';

const useStyles = makeStyles(theme => ({
  wrapper: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px',
    maxWidth: '88%',
    margin: '10px 0',
  },
  wrapperUser: {
    alignSelf: 'flex-end',
    flexDirection: 'row-reverse',
  },
  wrapperAi: {
    alignSelf: 'flex-start',
  },
  bubble: {
    padding: '13px 15px',
    borderRadius: '12px',
    boxShadow: 'none',
    fontFamily: 'Inter, "Segoe UI", Arial, sans-serif',
    lineHeight: 1.45,
    fontSize: '15px',
    color: '#17324d',
  },
  bubbleUser: {
    backgroundColor: '#dff7ea',
  },
  bubbleAi: {
    backgroundColor: '#edf2f7',
  },
  avatarUser: {
    backgroundColor: '#8cb4db', // Matches the blueish tint
  },
  avatarAi: {
    backgroundColor: '#f587a8', // Matches the pinkish tint from screenshot
  },
}));

type MessageBubbleProps = {
  role: 'user' | 'ai';
  text: string;
};

export const MessageBubble = ({ role, text }: MessageBubbleProps) => {
  const classes = useStyles();
  const isUser = role === 'user';

  const formatText = (rawText: string) => {
    let formattedText = rawText.replace(/\*\*(.*?)\*\*/g, '<b>$1</b>');
    formattedText = formattedText.replace(/`(.*?)`/g, '<code style="font-family: ui-monospace, Consolas, monospace; background: #f7fbff; border: 1px dashed #9fb3c8; padding: 2px 4px; border-radius: 4px; font-size: 13px;">$1</code>');
    formattedText = formattedText.replace(/\n/g, '<br>');
    return formattedText;
  };

  return (
    <div className={`${classes.wrapper} ${isUser ? classes.wrapperUser : classes.wrapperAi}`}>
      <Avatar className={isUser ? classes.avatarUser : classes.avatarAi}>
        {isUser ? <PersonIcon /> : <MemoryIcon />}
      </Avatar>
      <Paper className={`${classes.bubble} ${isUser ? classes.bubbleUser : classes.bubbleAi}`}>
        <Typography 
          variant="body1" 
          style={{ fontFamily: 'inherit', fontSize: 'inherit', lineHeight: 'inherit' }}
          dangerouslySetInnerHTML={{ __html: formatText(text) }} 
        />
      </Paper>
    </div>
  );
};
