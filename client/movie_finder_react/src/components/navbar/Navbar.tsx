import { useContext } from "react";
import { AppContext } from '../../App';

// Add the menu icon library
// You'll need to install lucide-react:
// npm install lucide-react

const Navbar = () => {
    const ctx = useContext(AppContext);

    if (!ctx) {
        return null; // Return null instead of nothing for best practices
    }

    return (
        <header>
            {/* <div className="container flex h-14 items-center justify-between">
                <div className="mr-4 md:flex">
                    <Link to="/" className="flex items-center space-x-2 font-bold text-lg">
                        Home
                    </Link>
                </div>

                <nav className="hidden md:flex items-center space-x-6 text-sm font-medium">
                    <Link to="/contact">
                        <Button variant="ghost">Contact</Button>
                    </Link>
                    <Link to="/about">
                        <Button variant="ghost">About</Button>
                    </Link>
                </nav>

                <Sheet>
                    <SheetTrigger asChild>
                        <Button
                            variant="ghost"
                            className="mr-2 px-0 text-base hover:bg-transparent focus-visible:bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 md:hidden"
                        >
                            <Menu className="h-6 w-6" />
                            <span className="sr-only">Toggle Menu</span>
                        </Button>
                    </SheetTrigger>
                    <SheetContent side="left" className="pr-0">
                        <Link
                            to="/"
                            className="flex items-center space-x-2 font-bold text-lg"
                        >
                            Home
                        </Link>
                        <nav className="mt-4 flex flex-col space-y-4">
                            <Link to="/contact">
                                <Button variant="ghost" className="w-full justify-start">Contact</Button>
                            </Link>
                            <Link to="/about">
                                <Button variant="ghost" className="w-full justify-start">About</Button>
                            </Link>
                        </nav>
                    </SheetContent>
                </Sheet>
            </div> */}
        </header>
    );
};

export default Navbar;