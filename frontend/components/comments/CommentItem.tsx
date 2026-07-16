"use client";
import {useState} from "react";
import {api} from "@/lib/api";
import type {Comment} from "@/lib/types";
import {Avatar} from "../Avatar";
import {LikeIcon,TrashIcon} from "../Icons";
import styles from "./CommentsSheet.module.css";

export function CommentItem({initial,onDeleted}:{initial:Comment;onDeleted:(id:string,count:number)=>void}) {
  const [comment,setComment]=useState(initial),[busy,setBusy]=useState(false);
  async function like(){if(busy)return;setBusy(true);try{const x=await api<{active:boolean;count:number}>(`/comments/${comment.id}/like/`,{method:comment.viewer_state.liked?"DELETE":"POST"});setComment(v=>({...v,viewer_state:{liked:x.active},counts:{...v.counts,likes:x.count}}))}finally{setBusy(false)}}
  async function remove(){if(!confirm("Delete this reply?"))return;setBusy(true);try{const x=await api<{deleted:boolean;post_comment_count:number}>(`/comments/${comment.id}/`,{method:"DELETE"});onDeleted(comment.id,x.post_comment_count)}finally{setBusy(false)}}
  return <article id={`comment-${comment.id}`} className={styles.comment}><Avatar user={comment.author} size={38}/><div><header><b>{comment.author.display_name}</b>{comment.author.username&&<span>@{comment.author.username}</span>}<small>· {new Date(comment.created_at).toLocaleDateString()}</small></header><p>{comment.body}</p><footer><button disabled={busy} onClick={()=>void like()} aria-label={comment.viewer_state.liked?"Unlike reply":"Like reply"}><LikeIcon fill={comment.viewer_state.liked?"currentColor":"none"}/><span>{comment.counts.likes}</span></button>{comment.counts.replies>0&&<span>{comment.counts.replies} {comment.counts.replies===1?"reply":"replies"}</span>}{comment.can_delete&&<button disabled={busy} onClick={()=>void remove()} aria-label="Delete reply"><TrashIcon/></button>}</footer></div></article>;
}
