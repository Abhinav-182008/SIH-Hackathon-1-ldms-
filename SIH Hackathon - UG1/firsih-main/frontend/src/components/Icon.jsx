import React from 'react'
const paths = {
  home: 'M3 10 12 3l9 7v10H3Z M9 20v-7h6v7',
  search: 'M10.5 18a7.5 7.5 0 1 0 0-15 7.5 7.5 0 0 0 0 15ZM16 16l5 5',
  upload: 'M12 16V3m-5 5 5-5 5 5 M4 15v6h16v-6',
  requests: 'M8 3h11v18H5V6h3V3Z M9 10h6 M9 14h6 M9 18h4',
  inbox: 'M3 13 6 4h12l3 9v7H3Z M3 13h5l2 3h4l2-3h5',
  bell: 'M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9 M10 21h4',
  audit: 'M12 3 3 7v6c0 5 9 9 9 9s9-4 9-9V7Z M8 12l3 3 5-6',
  sun: 'M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8 M12 2v2m0 16v2M2 12h2m16 0h2M5 5l1 1m12 12 1 1M5 19l1-1M18 6l1-1',
  moon: 'M20 14A9 9 0 0 1 10 3a9 9 0 1 0 10 11Z',
  arrow: 'M4 12h16m-6-6 6 6-6 6',
  check: 'm5 12 4 4L19 6',
  lock: 'M6 10h12v11H6Z M8 10V6a4 4 0 0 1 8 0v4 M12 14v3',
  clock: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18 M12 7v5l3 2',
  close: 'm6 6 12 12M6 18 18 6',
  file: 'M14 3H5v18h14V8Zm0 0v5h5 M8 12h8M8 16h5',
  logout: 'M9 3H3v18h6 M9 12h12m-5-5 5 5-5 5',
}
export default function Icon({ name, size = 20, ...props }) {
  return <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}><path d={paths[name] || paths.file} /></svg>
}
