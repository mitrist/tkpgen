import { type ComponentProps } from 'react';
import { type AsChildProp } from '../../../../types';
export type TypographyBodyVariant = 'large' | 'medium' | 'small' | 'small-strong' | 'small-caps' | 'custom';
export interface TypographyBodyProps extends ComponentProps<'span'>, AsChildProp {
    variant?: TypographyBodyVariant;
}
export declare const TypographyBody: import("react").ForwardRefExoticComponent<Omit<TypographyBodyProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=TypographyBody.d.ts.map