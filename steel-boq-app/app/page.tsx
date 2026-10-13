import Navbar from "@/components/ui/navbar";
import Hero from "@/components/ui/hero";
import FeaturesCards from "@/components/ui/feature-shader-cards";
import HowItWorks from "@/components/ui/how-it-works";
import Footer from "@/components/ui/footer";

export default function Home() {
  return (
    <>
      <Navbar />
      <main>
        <Hero />
        <section id="features">
          <FeaturesCards />
        </section>
        <HowItWorks />
      </main>
      <Footer />
    </>
  );
}
