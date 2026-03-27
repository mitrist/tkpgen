import { type ComponentProps } from 'react';
export type DotAppearance = 'themed' | 'contrast-pinned' | 'neutral-fade' | 'accent-red' | 'inherit';
export interface DotProps extends ComponentProps<'span'> {
    appearance?: DotAppearance;
}
export declare const Dot: import("react").ForwardRefExoticComponent<Omit<DotProps, "ref"> & import("react").RefAttributes<HTMLSpanElement>>;
//# sourceMappingURL=Dot.d.ts.map