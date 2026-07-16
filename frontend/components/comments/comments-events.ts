export const COMMENTS_UPDATED = "jesca:post-comments-updated";
export type CommentsUpdatedDetail = {postId: string; count: number};
export function publishCommentsCount(postId: string, count: number) {
  dispatchEvent(new CustomEvent<CommentsUpdatedDetail>(COMMENTS_UPDATED, {detail: {postId, count}}));
}

