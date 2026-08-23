const base = {
  fill: 'none',
  stroke: 'currentColor',
  strokeWidth: 1.7,
  strokeLinecap: 'round',
  strokeLinejoin: 'round',
}

export function LogoMark(props) {
  return (
    <svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true" {...base} {...props}>
      <path d="M6 3v5a4 4 0 0 0 8 0V3" />
      <path d="M4 3h3M13 3h3" />
      <path d="M10 12v3a5 5 0 0 0 10 0v-1" />
      <circle cx="20" cy="10" r="2" />
    </svg>
  )
}

export function PaperclipIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width="19" height="19" aria-hidden="true" {...base} {...props}>
      <path d="M21 11.5 12.5 20a5 5 0 0 1-7-7l8-8a3.5 3.5 0 0 1 5 5l-8 8a2 2 0 0 1-3-3l7.5-7.5" />
    </svg>
  )
}

export function SendIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" {...base} {...props}>
      <path d="m4 12 16-8-6 16-2.5-6.5L4 12Z" />
    </svg>
  )
}

export function CheckIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true" {...base} {...props}>
      <path d="m4 12 5 5L20 6" />
    </svg>
  )
}

export function PillIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" {...base} {...props}>
      <rect x="2.5" y="8" width="19" height="8" rx="4" />
      <path d="M12 8v8" />
    </svg>
  )
}

export function FileTextIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" {...base} {...props}>
      <path d="M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8l-5-5Z" />
      <path d="M14 3v5h5M9 13h6M9 17h4" />
    </svg>
  )
}

export function AlertIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" {...base} {...props}>
      <path d="M12 4 2.8 20h18.4L12 4Z" />
      <path d="M12 10v4M12 17.2v.1" />
    </svg>
  )
}

export function ImageIcon(props) {
  return (
    <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" {...base} {...props}>
      <rect x="3" y="4" width="18" height="16" rx="2" />
      <circle cx="8.5" cy="9.5" r="1.6" />
      <path d="m4 17 5-4.5 4 3.2L16.5 13 20 16" />
    </svg>
  )
}
