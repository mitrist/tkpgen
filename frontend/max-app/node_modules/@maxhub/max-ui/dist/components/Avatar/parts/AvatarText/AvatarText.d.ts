import { type ComponentProps } from 'react';
export type AvatarTextGradient = 'red' | 'orange' | 'green' | 'blue' | 'purple' | 'custom';
export interface AvatarTextProps extends ComponentProps<'span'> {
    gradient?: AvatarTextGradient;
}
export declare const AvatarText: import("react").ForwardRefExoticComponent<Omit<AvatarTextProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=AvatarText.d.ts.map