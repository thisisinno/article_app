const Line=({width="100%"}:{width?:string})=><span className="sk line" style={{width}}/>;
export function PostCardSkeleton({image=false}:{image?:boolean}){return <div className="postSkeleton" role="status"><div className="sk avatar"/><div className="skBody"><Line width="38%"/><Line width="24%"/><br/><Line/><Line width="92%"/><Line width="64%"/>{image&&<div className="sk image"/>}<div className="skActions">{[1,2,3,4,5].map(x=><span className="sk dot" key={x}/>)}</div></div><span className="srOnly">Loading posts</span></div>}
export function FeedSkeleton(){return <div aria-busy="true"><PostCardSkeleton/><PostCardSkeleton image/><PostCardSkeleton/></div>}
export function CategoryTabsSkeleton(){return <div className="categorySkeleton" role="status">{[52,90,76,105].map(x=><span className="sk pill" style={{width:x}} key={x}/>)}</div>}
export function CommentSkeleton(){return <div aria-busy="true">{[1,2,3].map(x=><div className="commentSkeleton" key={x}><span className="sk avatar"/><div><Line width="40%"/><Line/><Line width="72%"/></div></div>)}</div>}
export function ProfileSkeleton(){return <div aria-busy="true"><div className="sk profileCover"/><div className="sk profileAvatar"/><div className="profileLines"><Line width="35%"/><Line width="25%"/><Line width="70%"/></div><FeedSkeleton/></div>}
export function PostDetailSkeleton(){return <div aria-busy="true"><PostCardSkeleton image/><CommentSkeleton/></div>}
export function SearchSkeleton(){return <FeedSkeleton/>}
export function NotificationsSkeleton(){return <div aria-busy="true">{[1,2,3,4].map(x=><div className="notificationSkeleton" key={x}><span className="sk dot"/><span className="sk avatar"/><div><Line/><Line width="55%"/></div></div>)}</div>}
