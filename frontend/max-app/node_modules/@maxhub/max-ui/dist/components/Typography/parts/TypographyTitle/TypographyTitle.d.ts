import { type ComponentProps } from 'react';
import { type AsChildProp } from '../../../../types';
export type TypographyTitleVariant = 'large-strong' | 'medium-strong' | 'small' | 'small-strong' | 'custom';
export interface TypographyTitleProps extends ComponentProps<'span'>, AsChildProp {
    variant?: TypographyTitleVariant;
}
export declare const TypographyTitle: import("react").ForwardRefExoticComponent<Omit<TypographyTitleProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=TypographyTitle.d.ts.map