import { type ComponentProps, type ReactNode } from 'react';
import { type AsChildProp, type InnerClassNamesProp } from '../../../../types';
export type AvatarContainerElementKey = 'overlay' | 'content' | 'rightBottomCorner' | 'rightTopCorner';
export type AvatarContainerSize = 16 | 20 | 24 | 28 | 32 | 36 | 40 | 44 | 48 | 54 | 56 | 64 | 72 | 80 | 88 | 96 | number;
export type AvatarContainerFrom = 'circle' | 'squircle';
export interface AvatarContainerProps extends ComponentProps<'div'>, AsChildProp {
    size?: AvatarContainerSize;
    overlay?: ReactNode;
    form?: AvatarContainerFrom;
    innerClassNames?: InnerClassNamesProp<AvatarContainerElementKey>;
    rightTopCorner?: ReactNode;
    rightBottomCorner?: ReactNode;
}
export declare const AvatarContainer: import("react").ForwardRefExoticComponent<Omit<AvatarContainerProps, "ref"> & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=AvatarContainer.d.ts.map