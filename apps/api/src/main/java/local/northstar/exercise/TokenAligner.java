package local.northstar.exercise;

import java.util.*;
import java.util.regex.Pattern;

/** Unit-cost Levenshtein on English tokens; original input is stored separately. */
public final class TokenAligner {
    private static final Pattern TOKEN = Pattern.compile("[a-z0-9]+(?:'[a-z0-9]+)*");
    private TokenAligner() {}
    static List<String> tokens(String text) {
        return TOKEN.matcher(text.toLowerCase(Locale.ROOT).replace('’', '\'')).results().map(r -> r.group()).toList();
    }
    public static Result align(String expected, String actual) {
        var a = tokens(expected); var b = tokens(actual);
        int[][] d = new int[a.size()+1][b.size()+1];
        for (int i=0;i<=a.size();i++) d[i][0]=i;
        for (int j=0;j<=b.size();j++) d[0][j]=j;
        for (int i=1;i<=a.size();i++) for (int j=1;j<=b.size();j++)
            d[i][j]=Math.min(d[i-1][j-1]+(a.get(i-1).equals(b.get(j-1))?0:1),Math.min(d[i-1][j]+1,d[i][j-1]+1));
        var edits = new ArrayList<Edit>(); int i=a.size(),j=b.size();
        while(i>0 || j>0) {
            if(i>0 && j>0 && d[i][j]==d[i-1][j-1]+(a.get(i-1).equals(b.get(j-1))?0:1)) {
                edits.add(new Edit(a.get(i-1).equals(b.get(j-1))?"equal":"replace",a.get(i-1),b.get(j-1),i-1,j-1)); i--;j--;
            } else if(i>0 && d[i][j]==d[i-1][j]+1) { edits.add(new Edit("omit",a.get(i-1),"",i-1,j));i--; }
            else { edits.add(new Edit("insert","",b.get(j-1),i,j-1));j--; }
        }
        Collections.reverse(edits);
        return new Result(d[a.size()][b.size()]==0, "english_token_v1", edits);
    }
    public record Edit(String kind,String expected,String actual,int expectedIndex,int actualIndex) {}
    public record Result(boolean correct,String algorithmVersion,List<Edit> edits) {}
}
