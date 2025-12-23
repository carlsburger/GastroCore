/**
 * BackButton.jsx - Wiederverwendbare Zurück-Navigation
 * Sprint: Service-Terminal Polish Patch
 */
import React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "./ui/button";
import { ArrowLeft } from "lucide-react";

export const BackButton = ({ 
  to, 
  label = "Zurück", 
  fallback = "/",
  className = "",
  variant = "ghost"
}) => {
  const navigate = useNavigate();

  const handleClick = () => {
    if (to) {
      navigate(to);
    } else if (window.history.length > 2) {
      navigate(-1);
    } else {
      navigate(fallback);
    }
  };

  return (
    <Button
      variant={variant}
      onClick={handleClick}
      className={`text-stone-600 hover:text-stone-900 ${className}`}
    >
      <ArrowLeft className="h-4 w-4 mr-2" />
      {label}
    </Button>
  );
};

export default BackButton;
