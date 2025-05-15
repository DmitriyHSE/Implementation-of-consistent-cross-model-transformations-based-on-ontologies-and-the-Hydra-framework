package generated;

/** Высшее учебное заведение */
public class University {
    
    /** Название университета */
    private String name;
    
    /** Год основания */
    private String established;
    

    public University() {
        
        this.name = "";
        
        this.established = "";
        
    }

    
    public String getName() {
        return this.name;
    }

    public void setName(String name) {
        this.name = name;
    }
    
    public String getEstablished() {
        return this.established;
    }

    public void setEstablished(String established) {
        this.established = established;
    }
    

    @Override
    public String toString() {
        return "University{" +
            
            "name=" + name + ", " + 
            "established=" + established + "" +
            '}';
    }
}