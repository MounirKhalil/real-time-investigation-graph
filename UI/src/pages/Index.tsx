import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { toast } from "sonner";

type InterrogationMode = "question" | "answer";

interface InterrogationEntry {
  question: string;
  answer: string;
}

// Mock backend simulation
const simulateBackendResponse = async (history: InterrogationEntry[]) => {
  // Simulate network delay
  await new Promise(resolve => setTimeout(resolve, 1500));
  
  const suggestedQuestions = [
    "Can you provide more details about that location?",
    "Who else was present at that time?",
    "What time exactly did this occur?",
    "Why were you there specifically?",
    "Can anyone corroborate your statement?",
  ];
  
  // Return random suggestions
  const suggestions = [
    suggestedQuestions[Math.floor(Math.random() * suggestedQuestions.length)],
    suggestedQuestions[Math.floor(Math.random() * suggestedQuestions.length)],
  ];
  
  // Mock graph URL (placeholder)
  const graphUrl = "https://placehold.co/600x400/2d1810/d4b896?text=Knowledge+Graph";
  
  return { suggestions, graphUrl };
};

const Index = () => {
  const [mode, setMode] = useState<InterrogationMode>("question");
  const [currentText, setCurrentText] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [history, setHistory] = useState<InterrogationEntry[]>([]);
  const [suggestedQuestions, setSuggestedQuestions] = useState<string[]>([]);
  const [graphUrl, setGraphUrl] = useState<string>("");
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSubmit = async () => {
    if (!currentText.trim()) {
      toast.error("Please enter text before submitting");
      return;
    }

    if (mode === "question") {
      setCurrentQuestion(currentText);
      setCurrentText("");
      setMode("answer");
      toast.success("Question recorded. Awaiting suspect's answer...");
    } else {
      // Answer submitted - send to backend
      setIsProcessing(true);
      const newEntry: InterrogationEntry = {
        question: currentQuestion,
        answer: currentText,
      };
      
      const updatedHistory = [...history, newEntry];
      setHistory(updatedHistory);
      
      try {
        // send conversation to investigator assistant backend to save
        try {
          const saveResp = await fetch("http://localhost:8000/save_conversation", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(newEntry),
          });

          if (!saveResp.ok) {
            const bodyText = await saveResp.text().catch(() => "");
            console.error("Save endpoint returned non-OK:", saveResp.status, saveResp.statusText, bodyText);
            toast.error(`Save failed: ${saveResp.status} ${saveResp.statusText}`);
          } else {
            const data = await saveResp.json().catch(() => null);
            console.info("Saved conversation:", data);
            toast.success("Conversation saved");
          }
        } catch (e) {
          // If backend not available, continue with local simulation, but notify user
          console.error("Could not reach save backend:", e);
          toast.error("Could not save conversation: backend unreachable");
        }

        const response = await simulateBackendResponse(updatedHistory);
        setSuggestedQuestions(response.suggestions);
        setGraphUrl(response.graphUrl);
        toast.success("Analysis complete. Graph updated.");
      } catch (error) {
        toast.error("Failed to process interrogation data");
      }
      
      setCurrentText("");
      setCurrentQuestion("");
      setMode("question");
      setIsProcessing(false);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    setCurrentText(suggestion);
  };

  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b-2 border-primary p-6 leather-texture">
        <h1 className="text-4xl font-bold text-center text-primary">
          Holmes Interrogation System
        </h1>
        <p className="text-center text-muted-foreground mt-2 italic">
          "Elementary, my dear Watson" - A systematic approach to truth
        </p>
      </header>

      {/* Main Content */}
      <main className="flex-1 flex">
        {/* Left Side - Graph and Analysis */}
        <div className="w-1/2 border-r-2 border-primary p-6 vintage-texture">
          <Card className="h-full p-6 bg-card border-2 border-primary">
            <h2 className="text-2xl font-bold text-primary mb-4 border-b border-border pb-2">
              Knowledge Graph & Analysis
            </h2>
            
            {graphUrl ? (
              <div className="flex flex-col h-[calc(100%-4rem)]">
                <img 
                  src={graphUrl} 
                  alt="Knowledge Graph" 
                  className="w-full h-auto border-2 border-border rounded"
                />
              </div>
            ) : (
              <div className="flex items-center justify-center h-[calc(100%-4rem)] text-muted-foreground italic border-2 border-dashed border-border rounded">
                <p>Graph will appear here after first interrogation cycle</p>
              </div>
            )}
          </Card>
        </div>

        {/* Right Side - Q&A Area */}
        <div className="w-1/2 p-6 flex flex-col">
          <Card className="flex-1 p-6 bg-card border-2 border-primary flex flex-col">
            <h2 className="text-2xl font-bold text-primary mb-4 border-b border-border pb-2">
              Interrogation Room
            </h2>
            
            {/* Current Question/Answer Input */}
            <div className="mb-6">
              <label className="block text-lg font-semibold text-foreground mb-2">
                {mode === "question" ? "Investigator Question" : "Suspect Answer"}
              </label>
              <Textarea
                value={currentText}
                onChange={(e) => setCurrentText(e.target.value)}
                placeholder={mode === "question" 
                  ? "Enter your question for the suspect..." 
                  : "Suspect's response..."}
                className="min-h-[120px] bg-input text-foreground border-border resize-none"
                disabled={isProcessing}
              />
              <Button
                onClick={handleSubmit}
                disabled={isProcessing}
                className="mt-4 w-full bg-primary hover:bg-primary/90 text-primary-foreground font-semibold"
              >
                {isProcessing ? "Processing..." : "Submit"}
              </Button>
            </div>

            {/* Suggested Questions */}
            {mode === "question" && suggestedQuestions.length > 0 && (
              <div className="mb-6">
                <label className="block text-lg font-semibold text-secondary mb-2">
                  Suggested Questions
                </label>
                <div className="space-y-2">
                  {suggestedQuestions.map((suggestion, index) => (
                    <Button
                      key={index}
                      variant="outline"
                      onClick={() => handleSuggestionClick(suggestion)}
                      className="w-full text-left justify-start h-auto py-3 px-4 bg-secondary/10 hover:bg-secondary/20 border-secondary text-foreground"
                    >
                      {suggestion}
                    </Button>
                  ))}
                </div>
              </div>
            )}

            {/* History Log */}
            <div className="flex-1 overflow-auto">
              <h3 className="text-lg font-semibold text-primary mb-3 border-b border-border pb-1">
                Investigation Log
              </h3>
              <div className="space-y-4">
                {history.length === 0 ? (
                  <p className="text-muted-foreground italic">
                    No entries yet. Begin the interrogation...
                  </p>
                ) : (
                  history.map((entry, index) => (
                    <div key={index} className="border-l-4 border-primary pl-4 py-2 bg-muted/30 rounded-r">
                      <p className="font-semibold text-sm text-primary">Q:</p>
                      <p className="mb-2 text-sm">{entry.question}</p>
                      <p className="font-semibold text-sm text-secondary">A:</p>
                      <p className="text-sm">{entry.answer}</p>
                    </div>
                  ))
                )}
              </div>
            </div>
          </Card>
        </div>
      </main>
    </div>
  );
};

export default Index;
