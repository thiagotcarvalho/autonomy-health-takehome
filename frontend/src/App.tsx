import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

function App() {
  return (
    <div className="min-h-svh flex items-center justify-center p-8 bg-background text-foreground">
      <Card className="w-full max-w-md">
        <CardHeader>
          <CardTitle>FHIR Prior Authorization Review</CardTitle>
          <CardDescription>Bundle 6A — scaffold smoke test</CardDescription>
        </CardHeader>
        <CardContent>
          <Button>Tailwind + shadcn working</Button>
        </CardContent>
      </Card>
    </div>
  );
}

export default App;
