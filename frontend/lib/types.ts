export type User={id:string;username:string|null;display_name:string;avatar:string|null;verified:boolean;is_staff:boolean;is_superuser:boolean;can_publish:boolean};
export type Category={id:number;name:string;slug:string;description:string};
export type Post={id:string;type:"short"|"article";title:string;body:string;excerpt:string;author:User;category:Pick<Category,"id"|"name"|"slug">|null;cover_image:string|null;pinned:boolean;featured:boolean;published_at:string;counts:{views:number;likes:number;comments:number;bookmarks:number;shares:number};viewer_state:{liked:boolean;bookmarked:boolean;can_edit:boolean};thread?:Post[]};
export type Comment={id:string;body:string;author:User;created_at:string;counts:{likes:number;replies:number};viewer_state:{liked:boolean};can_delete:boolean;replies:Comment[]};
export type Notification={id:string;kind:string;actor:User|null;text:string;post:{id:string;title:string;preview:string}|null;comment_id:string|null;read:boolean;created_at:string};
