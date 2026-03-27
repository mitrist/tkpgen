import { type ComponentProps } from 'react';
import { type MaxUIContextInterface } from './MaxUIContext';
export interface MaxUIProps extends Partial<MaxUIContextInterface> {
    children: ComponentProps<'div'>['children'];
    className?: ComponentProps<'div'>['className'];
}
export declare const MaxUI: import("react").ForwardRefExoticComponent<MaxUIProps & import("react").RefAttributes<HTMLDivElement>>;
//# sourceMappingURL=MaxUI.d.ts.map