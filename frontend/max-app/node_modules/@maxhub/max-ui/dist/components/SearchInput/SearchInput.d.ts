import { type ComponentProps } from 'react';
import { type InnerClassNamesProp } from '../../types';
export type SearchInputElementKey = 'input' | 'clearButton' | 'body';
export interface SearchInputProps extends ComponentProps<'input'> {
    innerClassNames?: InnerClassNamesProp<SearchInputElementKey>;
}
export declare const SearchInput: import("react").ForwardRefExoticComponent<Omit<SearchInputProps, "ref"> & import("react").RefAttributes<HTMLInputElement>>;
//# sourceMappingURL=SearchInput.d.ts.map