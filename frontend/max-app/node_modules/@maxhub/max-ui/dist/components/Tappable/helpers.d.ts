import { type AllHTMLAttributes } from 'react';
import { type AsChildProp } from '../../types';
interface ExpectedProps extends AsChildProp {
    onClick?: AllHTMLAttributes<HTMLElement>['onClick'];
    href?: AllHTMLAttributes<HTMLElement>['href'];
    children?: AllHTMLAttributes<HTMLElement>['children'];
    parentChildren?: AllHTMLAttributes<HTMLElement>['children'];
}
export declare const checkComponentHasAction: ({ onClick, href, children, asChild, parentChildren }: ExpectedProps) => boolean;
export {};
//# sourceMappingURL=helpers.d.ts.map