import { type ComponentProps, type ReactNode } from 'react';
import { type AvatarTextGradient } from '../AvatarText';
export interface AvatarImageProps extends ComponentProps<'img'> {
    fallback?: ReactNode;
    fallbackGradient?: AvatarTextGradient;
}
export declare const AvatarImage: import("react").ForwardRefExoticComponent<Omit<AvatarImageProps, "ref"> & import("react").RefAttributes<HTMLImageElement>>;
//# sourceMappingURL=AvatarImage.d.ts.map