import { makeStyles } from '@material-ui/core/styles';
import { Typography, Paper, Avatar } from '@material-ui/core';
import PersonIcon from '@material-ui/icons/Person';
import MemoryIcon from '@material-ui/icons/Memory';

const useStyles = makeStyles(theme => ({
  wrapper: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: `${theme.spacing(2)}px`,
    maxWidth: '80%',
  },
  wrapperUser: {
    alignSelf: 'flex-end',
    flexDirection: 'row-reverse',
  },
  wrapperAi: {
    alignSelf: 'flex-start',
  },
  bubble: {
    padding: theme.spacing(2),
    borderRadius: theme.shape.borderRadius,
    boxShadow: theme.shadows[1],
  },
  bubbleUser: {
    backgroundColor: theme.palette.primary.main,
    color: theme.palette.primary.contrastText,
    borderBottomRightRadius: 0,
  },
  bubbleAi: {
    backgroundColor: theme.palette.background.paper,
    color: theme.palette.text.primary,
    borderBottomLeftRadius: 0,
  },
  avatarUser: {
    backgroundColor: theme.palette.primary.dark,
  },
  avatarAi: {
    backgroundColor: theme.palette.secondary.main,
  },
}));

type MessageBubbleProps = {
  role: 'user' | 'ai';
  text: string;
};

export const MessageBubble = ({ role, text }: MessageBubbleProps) => {
  const classes = useStyles();
  const isUser = role === 'user';

  return (
    <div className={`${classes.wrapper} ${isUser ? classes.wrapperUser : classes.wrapperAi}`}>
      <Avatar className={isUser ? classes.avatarUser : classes.avatarAi}>
        {isUser ? <PersonIcon /> : <MemoryIcon />}
      </Avatar>
      <Paper className={`${classes.bubble} ${isUser ? classes.bubbleUser : classes.bubbleAi}`}>
        <Typography variant="body1">{text}</Typography>
      </Paper>
    </div>
  );
};
