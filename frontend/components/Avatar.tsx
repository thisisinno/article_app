import type {User} from "@/lib/types";
import styles from "./Avatar.module.css";
type AvatarProps={user?:Pick<User,"avatar"|"display_name"|"username">|null;name?:string;size?:number;variant?:"user"|"brand"|"guest";className?:string};
const pick=(value:string,fallback:string)=>Array.from(value.trim()).find(c=>/[\p{L}\p{N}]/u.test(c))?.toUpperCase()||fallback;
export function Avatar({user,name,size=40,variant="user",className=""}:AvatarProps){const label=name||user?.display_name||user?.username||"",fallback=variant==="brand"?"J":"R";return user?.avatar?<img className={`${styles.image} avatarImage ${className}`} src={user.avatar} width={size} height={size} alt={`${label||"User"} profile picture`}/>:<span className={`${styles.fallback} ${styles[variant]} avatarFallback ${className}`} style={{width:size,height:size,fontSize:Math.max(12,Math.round(size*.4))}} role="img" aria-label={`${label||fallback} avatar`}>{pick(label,fallback)}</span>}
