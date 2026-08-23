import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { LogoMark } from './icons'

function Message({ role, content, pending }) {
  const isAssistant = role === 'assistant'

  return (
    <article className={`msg ${role}`}>
      {isAssistant && (
        <span className="msg-avatar" aria-hidden="true">
          <LogoMark width="15" height="15" />
        </span>
      )}

      <div className="msg-body">
        {pending ? (
          <span className="typing" role="status" aria-label="Assistant is typing">
            <i />
            <i />
            <i />
          </span>
        ) : isAssistant ? (
          <div className="prose">
            <Markdown remarkPlugins={[remarkGfm]}>{content}</Markdown>
          </div>
        ) : (
          <p>{content}</p>
        )}
      </div>
    </article>
  )
}

export default Message
