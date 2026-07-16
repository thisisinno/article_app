import type {SVGProps} from "react";
type Props=SVGProps<SVGSVGElement>;
function Icon({children,...props}:Props&{children:React.ReactNode}){return <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" {...props}>{children}</svg>}
export const HomeIcon=(p:Props)=><Icon {...p}><path d="m3 11 9-8 9 8v9a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z"/></Icon>;
export const SearchIcon=(p:Props)=><Icon {...p}><circle cx="11" cy="11" r="7"/><path d="m20 20-4-4"/></Icon>;
export const BellIcon=(p:Props)=><Icon {...p}><path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4"/></Icon>;
export const ProfileIcon=(p:Props)=><Icon {...p}><circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/></Icon>;
export const ComposeIcon=(p:Props)=><Icon {...p}><path d="M12 20h9M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4z"/></Icon>;
export const CommentIcon=(p:Props)=><Icon {...p}><path d="M21 15a4 4 0 0 1-4 4H8l-5 3V7a4 4 0 0 1 4-4h10a4 4 0 0 1 4 4z"/></Icon>;
export const LikeIcon=(p:Props)=><Icon {...p}><path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8z"/></Icon>;
export const BookmarkIcon=(p:Props)=><Icon {...p}><path d="M6 3h12v18l-6-4-6 4z"/></Icon>;
export const ViewIcon=(p:Props)=><Icon {...p}><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12z"/><circle cx="12" cy="12" r="3"/></Icon>;
export const ShareIcon=(p:Props)=><Icon {...p}><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><path d="m8.6 10.5 6.8-4M8.6 13.5l6.8 4"/></Icon>;
export const MoreIcon=(p:Props)=><Icon {...p}><circle cx="5" cy="12" r="1" fill="currentColor"/><circle cx="12" cy="12" r="1" fill="currentColor"/><circle cx="19" cy="12" r="1" fill="currentColor"/></Icon>;
export const CloseIcon=(p:Props)=><Icon {...p}><path d="m6 6 12 12M18 6 6 18"/></Icon>;
export const TrashIcon=(p:Props)=><Icon {...p}><path d="M3 6h18M8 6V4h8v2m3 0-1 15H6L5 6m5 4v7m4-7v7"/></Icon>;
export const LogoutIcon=(p:Props)=><Icon {...p}><path d="M10 17l5-5-5-5m5 5H3m10-9h7v18h-7"/></Icon>;
